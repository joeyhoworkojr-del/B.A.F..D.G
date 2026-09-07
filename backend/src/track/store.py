"""
Row storage for the ledger.

The ledger does all of its arithmetic in Python — Brier scores, P/L, hit rates
are computed from rows, not by the database. What it actually needs from
storage is six operations, which makes the backend genuinely interchangeable:

    upsert_pregame   conditional insert-or-refresh
    mark_graded      settle a row against a final score, once
    get              one row by event id
    rows             every row, optionally filtered to graded
    count            how many are graded / ungraded
    clear            wipe (tests)

Two implementations ship:

  SqlStore    SQLite by default, Postgres when DATABASE_URL is set.
  RedisStore  Redis or Upstash, when REDIS_URL / UPSTASH_REDIS_URL is set.

Both preserve the integrity rule that matters: a prediction may only be
refreshed while it is ungraded and while the model version still matches, so a
newer model cannot rewrite a call an older one is being judged on.
"""
from __future__ import annotations

import json
import logging
import os
import re
from typing import Any, Optional

from . import db

log = logging.getLogger(__name__)

_KEY_PREFIX = "statedge:pred:"
_INDEX_KEY = "statedge:pred:index"

# Every column the ledger reads back, so a KV row has the same shape a SQL row
# does and the callers above cannot tell the difference.
FIELDS = (
    "event_id", "league", "kickoff", "home", "away", "snapshot_at",
    "model_home_prob", "model_total", "book_home_prob", "crowd_home_prob",
    "market_spread", "market_total", "graded", "home_score", "away_score",
    "home_won", "graded_at", "home_code", "away_code", "home_elo", "away_elo",
    "elo_applied", "consensus_home_prob", "model_version", "book_source",
    "closing_spread", "closing_total", "closing_home_prob",
)


def redis_url() -> str:
    """The configured Redis URL, or "" when not using a KV backend."""
    for var in ("REDIS_URL", "UPSTASH_REDIS_URL", "KV_URL"):
        url = (os.getenv(var) or "").strip()
        if url.startswith(("redis://", "rediss://")):
            return url
    return ""


class SqlStore:
    """SQLite or Postgres, whichever db.py resolves."""

    name = "sql"

    def __init__(self, schema: str, migrations: list[tuple[str, str]], table: str):
        self._schema, self._migrations, self._table = schema, migrations, table

    def _connect(self):
        return db.connect(self._schema, self._migrations, self._table)

    @property
    def backend(self) -> str:
        return db.backend_name()

    @property
    def durable(self) -> bool:
        return db.is_postgres()

    def upsert_pregame(self, row: dict[str, Any]) -> None:
        cols = [
            "event_id", "league", "kickoff", "home", "away", "snapshot_at",
            "model_home_prob", "model_total", "book_home_prob",
            "crowd_home_prob", "market_spread", "market_total",
            "home_code", "away_code", "home_elo", "away_elo",
            "consensus_home_prob", "model_version", "book_source",
        ]
        refresh = [c for c in cols if c not in ("event_id", "league", "kickoff",
                                                "home", "away", "model_version")]
        sets = ",\n                ".join(f"{c} = excluded.{c}" for c in refresh)
        with self._connect() as conn:
            conn.execute(
                f"""
                INSERT INTO {self._table} ({', '.join(cols)})
                VALUES ({', '.join('?' for _ in cols)})
                ON CONFLICT(event_id) DO UPDATE SET
                    {sets}
                WHERE {self._table}.graded = 0
                  AND ({self._table}.model_version IS NULL
                       OR {self._table}.model_version = excluded.model_version)
                """,
                tuple(row.get(c) for c in cols),
            )

    def mark_graded(self, event_id: str, home_score: int, away_score: int,
                    home_won: int, graded_at: str) -> bool:
        with self._connect() as conn:
            cur = conn.execute(
                f"""
                UPDATE {self._table}
                SET graded = 1, home_score = ?, away_score = ?,
                    home_won = ?, graded_at = ?,
                    closing_spread    = COALESCE(closing_spread, market_spread),
                    closing_total     = COALESCE(closing_total, market_total),
                    closing_home_prob = COALESCE(closing_home_prob, book_home_prob)
                WHERE event_id = ? AND graded = 0
                """,
                (home_score, away_score, home_won, graded_at, event_id),
            )
            return cur.rowcount > 0

    def get(self, event_id: str) -> Optional[dict]:
        with self._connect() as conn:
            row = conn.execute(
                f"SELECT * FROM {self._table} WHERE event_id = ?", (event_id,),
            ).fetchone()
            return dict(row) if row else None

    def rows(self, graded: Optional[bool] = None) -> list[dict]:
        clause = "" if graded is None else f" WHERE graded = {1 if graded else 0}"
        with self._connect() as conn:
            return [dict(r) for r in
                    conn.execute(f"SELECT * FROM {self._table}{clause}").fetchall()]

    def count(self, graded: bool) -> int:
        with self._connect() as conn:
            row = conn.execute(
                f"SELECT COUNT(*) AS n FROM {self._table} WHERE graded = ?",
                (1 if graded else 0,),
            ).fetchone()
            return int(row["n"])

    def clear(self) -> None:
        with self._connect() as conn:
            conn.execute(f"DELETE FROM {self._table}")


class RedisStore:
    """
    Redis / Upstash.

    Each prediction is a JSON string at `statedge:pred:{event_id}`, with a set
    holding every id so a full scan needs no KEYS command. The conditional
    upsert and the grade are read-modify-writes, which must not interleave, so
    both run as Lua inside Redis rather than as three round trips.
    """

    name = "redis"

    # Refresh only while ungraded and while the model version still matches.
    _UPSERT = """
    local key = KEYS[1]
    local index = KEYS[2]
    local incoming = cjson.decode(ARGV[1])
    local existing = redis.call('GET', key)
    if existing then
      local prev = cjson.decode(existing)
      if tonumber(prev['graded'] or 0) == 1 then return 0 end
      if prev['model_version'] and prev['model_version'] ~= cjson.null
         and incoming['model_version'] and incoming['model_version'] ~= cjson.null
         and prev['model_version'] ~= incoming['model_version'] then return 0 end
      for _, f in ipairs({'graded','home_score','away_score','home_won','graded_at',
                          'closing_spread','closing_total','closing_home_prob'}) do
        if prev[f] ~= nil then incoming[f] = prev[f] end
      end
    end
    redis.call('SET', key, cjson.encode(incoming))
    redis.call('SADD', index, ARGV[2])
    return 1
    """

    _GRADE = """
    local key = KEYS[1]
    local existing = redis.call('GET', key)
    if not existing then return 0 end
    local row = cjson.decode(existing)
    if tonumber(row['graded'] or 0) == 1 then return 0 end
    row['graded'] = 1
    row['home_score'] = tonumber(ARGV[1])
    row['away_score'] = tonumber(ARGV[2])
    row['home_won'] = tonumber(ARGV[3])
    row['graded_at'] = ARGV[4]
    if row['closing_spread'] == nil or row['closing_spread'] == cjson.null then
      row['closing_spread'] = row['market_spread'] end
    if row['closing_total'] == nil or row['closing_total'] == cjson.null then
      row['closing_total'] = row['market_total'] end
    if row['closing_home_prob'] == nil or row['closing_home_prob'] == cjson.null then
      row['closing_home_prob'] = row['book_home_prob'] end
    redis.call('SET', key, cjson.encode(row))
    return 1
    """

    def __init__(self, client=None):
        self._client = client
        self._upsert = None
        self._grade = None

    @property
    def backend(self) -> str:
        return "redis"

    @property
    def durable(self) -> bool:
        return True

    def _redis(self):
        if self._client is None:
            import redis
            self._client = redis.from_url(redis_url(), decode_responses=True)
        return self._client

    def _scripts(self):
        if self._upsert is None:
            client = self._redis()
            self._upsert = client.register_script(self._UPSERT)
            self._grade = client.register_script(self._GRADE)
        return self._upsert, self._grade

    @staticmethod
    def _blank(event_id: str) -> dict:
        return {f: None for f in FIELDS} | {"event_id": event_id, "graded": 0}

    def upsert_pregame(self, row: dict[str, Any]) -> None:
        upsert, _ = self._scripts()
        event_id = row["event_id"]
        payload = self._blank(event_id) | {k: v for k, v in row.items() if k in FIELDS}
        upsert(keys=[_KEY_PREFIX + event_id, _INDEX_KEY],
               args=[json.dumps(payload), event_id])

    def mark_graded(self, event_id: str, home_score: int, away_score: int,
                    home_won: int, graded_at: str) -> bool:
        _, grade = self._scripts()
        return bool(grade(keys=[_KEY_PREFIX + event_id],
                          args=[home_score, away_score, home_won, graded_at]))

    def get(self, event_id: str) -> Optional[dict]:
        raw = self._redis().get(_KEY_PREFIX + event_id)
        return json.loads(raw) if raw else None

    def rows(self, graded: Optional[bool] = None) -> list[dict]:
        client = self._redis()
        ids = sorted(client.smembers(_INDEX_KEY) or [])
        if not ids:
            return []
        raws = client.mget([_KEY_PREFIX + i for i in ids])
        out = [json.loads(r) for r in raws if r]
        if graded is None:
            return out
        want = 1 if graded else 0
        return [r for r in out if int(r.get("graded") or 0) == want]

    def count(self, graded: bool) -> int:
        return len(self.rows(graded=graded))

    def clear(self) -> None:
        client = self._redis()
        ids = client.smembers(_INDEX_KEY) or []
        if ids:
            client.delete(*[_KEY_PREFIX + i for i in ids])
        client.delete(_INDEX_KEY)


# Every variable the storage layer will look at, in precedence order.
_CONFIG_VARS = ("REDIS_URL", "UPSTASH_REDIS_URL", "KV_URL", "DATABASE_URL")

_ACCEPTED_SCHEMES = {
    "REDIS_URL": ("redis://", "rediss://"),
    "UPSTASH_REDIS_URL": ("redis://", "rediss://"),
    "KV_URL": ("redis://", "rediss://"),
    "DATABASE_URL": ("postgres://", "postgresql://"),
}


def config_report() -> dict:
    """
    Which storage variables this process can see, and whether each is usable.

    Names and scheme validity only — never a value, not even partially. The
    point is to answer "is the key missing, or is it the wrong kind of URL?"
    without a secret leaving the server, because that question has otherwise
    needed a round trip through someone's dashboard to settle.
    """
    present, usable, wrong_scheme = [], [], []
    for var in _CONFIG_VARS:
        raw = (os.getenv(var) or "").strip()
        if not raw:
            continue
        present.append(var)
        if raw.startswith(_ACCEPTED_SCHEMES[var]):
            usable.append(var)
        else:
            # e.g. Upstash's https:// REST endpoint pasted where the Redis
            # connection string belongs.
            wrong_scheme.append(var)

    # Upstash and Vercel generate several names — UPSTASH_REDIS_REST_URL and
    # UPSTASH_REDIS_REST_TOKEN among them — and none of those is the connection
    # string this backend opens. Naming what IS set turns "nothing is
    # configured" into "you set the wrong one of these".
    related = sorted(
        name for name in os.environ
        if name not in _CONFIG_VARS
        and any(tok in name.upper() for tok in ("REDIS", "UPSTASH", "KV_", "POSTGRES", "DATABASE"))
    )

    if usable:
        hint = ""
    elif wrong_scheme:
        hint = (
            f"{', '.join(wrong_scheme)} is set but its scheme is not one this "
            "backend can open. Redis needs redis:// or rediss:// (Upstash's "
            "https:// REST endpoint will not work); Postgres needs postgres://."
        )
    elif related:
        hint = (
            f"None of {', '.join(_CONFIG_VARS)} is set, but these related "
            f"variables are: {', '.join(related)}. Redis needs the connection "
            "string (rediss://...), not the REST URL or token — copy it into "
            "REDIS_URL."
        )
    else:
        hint = (
            "No storage variable is set on this process. Note the API runs on "
            "Fly, so the value must be a Fly secret — setting it anywhere else "
            "has no effect here."
        )

    if _redis_error:
        hint = (
            f"Redis is configured but could not be reached, so storage fell "
            f"back to SQLite. The driver reported: {_redis_error}"
        )

    return {
        "checked": list(_CONFIG_VARS),
        "redis_error": _redis_error,
        "present": present,
        "usable": usable,
        "wrong_scheme": wrong_scheme,
        # Names only, never values — env var names are not secrets, the
        # strings they hold are.
        "other_storage_vars_seen": related,
        "hint": hint,
    }


# Set when a configured Redis could not be used, so the diagnostic can say why
# without anyone reading logs. Scrubbed of credentials before it is stored.
_redis_error: str = ""


def redis_error() -> str:
    return _redis_error


def _scrub(text: str) -> str:
    """
    Strip credentials out of a driver error before it can be reported.

    redis-py puts the whole connection URL in its connection errors, password
    included, and this message is surfaced on a public endpoint.
    """
    scrubbed = re.sub(r"://[^@\s]*@", "://***@", str(text))
    return scrubbed[:300]


def build_store(schema: str, migrations: list[tuple[str, str]], table: str):
    """
    Whichever backend the environment configures. Redis wins when both are set.

    A configured Redis that cannot actually be reached falls back to SQL rather
    than propagating. Storage being misconfigured must not take the site down:
    the ledger is one feature, and every page that shows a live score would 500
    alongside it.
    """
    global _redis_error
    if redis_url():
        try:
            store = RedisStore()
            store._redis().ping()
            _redis_error = ""
            return store
        except Exception as exc:
            _redis_error = _scrub(exc)
            log.error("Redis configured but unusable, falling back to SQL: %s",
                      _redis_error)
    return SqlStore(schema, migrations, table)
