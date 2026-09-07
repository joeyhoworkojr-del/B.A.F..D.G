"""Storage backend selection and the SQLite/Postgres differences it reconciles."""
from __future__ import annotations

import pytest

from src.track import db, ledger


# ─── Backend selection ───────────────────────────────────────────────────────

def test_defaults_to_sqlite_when_no_database_url(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    assert db.is_postgres() is False
    assert db.backend_name() == "sqlite"


def test_postgres_is_selected_from_the_url(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql://u:p@host/db")
    assert db.is_postgres() is True
    assert db.backend_name() == "postgres"


def test_the_postgres_scheme_alias_is_accepted(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgres://u:p@host/db")
    assert db.is_postgres() is True


def test_a_non_postgres_url_does_not_switch_backends(monkeypatch):
    """A URL we cannot open must not disable SQLite and fail every write."""
    monkeypatch.setenv("DATABASE_URL", "mysql://u:p@host/db")
    assert db.is_postgres() is False
    assert db.backend_name() == "sqlite"


def test_an_empty_url_is_treated_as_unset(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "   ")
    assert db.is_postgres() is False


# ─── Placeholder translation ─────────────────────────────────────────────────

def test_placeholders_are_rewritten_for_psycopg(monkeypatch):
    assert db.to_pg_params("SELECT * FROM t WHERE a = ? AND b = ?") == \
        "SELECT * FROM t WHERE a = %s AND b = %s"


def test_a_question_mark_inside_a_literal_is_left_alone():
    sql = "SELECT * FROM t WHERE note = 'why? because' AND a = ?"
    assert db.to_pg_params(sql) == \
        "SELECT * FROM t WHERE note = 'why? because' AND a = %s"


def test_double_quoted_identifiers_are_left_alone():
    sql = 'SELECT "odd?name" FROM t WHERE a = ?'
    assert db.to_pg_params(sql) == 'SELECT "odd?name" FROM t WHERE a = %s'


def test_sql_without_placeholders_is_unchanged():
    sql = "DELETE FROM predictions"
    assert db.to_pg_params(sql) == sql


# ─── Durability reporting ────────────────────────────────────────────────────

def test_sqlite_is_reported_as_not_durable(monkeypatch):
    """
    The container disk is replaced on deploy, so a SQLite record is not
    permanent — and the product must not imply that it is.
    """
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("LEDGER_DURABLE", raising=False)
    assert ledger.storage_durable() is False


def test_postgres_is_reported_as_durable(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql://u:p@host/db")
    assert ledger.storage_durable() is True


def test_a_mounted_volume_can_be_declared_durable(monkeypatch):
    """A SQLite file on an attached volume does survive; let the operator say so."""
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.setenv("LEDGER_DURABLE", "1")
    assert ledger.storage_durable() is True


# ─── The ledger still works through the shim ─────────────────────────────────

def test_a_prediction_round_trips_on_the_default_backend(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    ledger.reset()
    ledger.record_pregame(
        event_id="nfl:storage-1", league="nfl",
        kickoff="2026-09-05T18:00:00+00:00",
        home="KC", away="BUF", model_home_prob=0.61,
        model_version="storage-test",
    )
    assert ledger.grade("nfl:storage-1", home_score=27, away_score=24) is True
    snap = ledger.get_snapshot("nfl:storage-1")
    assert snap is not None
    assert snap["model_version"] == "storage-test"


# ─── Redis / Upstash backend ─────────────────────────────────────────────────

class FakeRedis:
    """
    Enough Redis to exercise RedisStore without a server.

    The Lua scripts are the part that must not be skipped — the conditional
    upsert is where the integrity rule lives — so they are re-implemented here
    in Python with the same semantics rather than stubbed out.
    """

    def __init__(self):
        self.strings: dict[str, str] = {}
        self.sets: dict[str, set] = {}

    def register_script(self, body: str):
        upsert = "SADD" in body

        def run(keys, args):
            import json as _json
            if upsert:
                key, index = keys
                incoming = _json.loads(args[0])
                prev_raw = self.strings.get(key)
                if prev_raw:
                    prev = _json.loads(prev_raw)
                    if int(prev.get("graded") or 0) == 1:
                        return 0
                    if (prev.get("model_version") and incoming.get("model_version")
                            and prev["model_version"] != incoming["model_version"]):
                        return 0
                    for f in ("graded", "home_score", "away_score", "home_won",
                              "graded_at", "closing_spread", "closing_total",
                              "closing_home_prob"):
                        if prev.get(f) is not None:
                            incoming[f] = prev[f]
                self.strings[key] = _json.dumps(incoming)
                self.sets.setdefault(index, set()).add(args[1])
                return 1

            key = keys[0]
            raw = self.strings.get(key)
            if not raw:
                return 0
            row = _json.loads(raw)
            if int(row.get("graded") or 0) == 1:
                return 0
            row.update(graded=1, home_score=int(args[0]), away_score=int(args[1]),
                       home_won=int(args[2]), graded_at=args[3])
            for closing, source in (("closing_spread", "market_spread"),
                                    ("closing_total", "market_total"),
                                    ("closing_home_prob", "book_home_prob")):
                if row.get(closing) is None:
                    row[closing] = row.get(source)
            self.strings[key] = _json.dumps(row)
            return 1

        return run

    def get(self, key): return self.strings.get(key)
    def smembers(self, key): return set(self.sets.get(key, set()))
    def mget(self, keys): return [self.strings.get(k) for k in keys]

    def delete(self, *keys):
        for k in keys:
            self.strings.pop(k, None)
            self.sets.pop(k, None)


@pytest.fixture
def redis_store():
    from src.track.store import RedisStore
    return RedisStore(client=FakeRedis())


def test_redis_url_is_detected(monkeypatch):
    monkeypatch.setenv("UPSTASH_REDIS_URL", "rediss://default:tok@eu1.upstash.io:6379")
    assert db_store_redis_url() == "rediss://default:tok@eu1.upstash.io:6379"


def db_store_redis_url():
    from src.track import store
    return store.redis_url()


def test_a_non_redis_url_is_ignored(monkeypatch):
    monkeypatch.delenv("REDIS_URL", raising=False)
    monkeypatch.delenv("UPSTASH_REDIS_URL", raising=False)
    monkeypatch.setenv("KV_URL", "https://not-a-redis-url")
    assert db_store_redis_url() == ""


def test_redis_is_always_reported_durable(redis_store):
    assert redis_store.durable is True
    assert redis_store.backend == "redis"


def test_a_prediction_round_trips_through_redis(redis_store):
    redis_store.upsert_pregame({
        "event_id": "nfl:1", "league": "nfl", "home": "KC", "away": "BUF",
        "model_home_prob": 0.61, "model_version": "v1",
    })
    row = redis_store.get("nfl:1")
    assert row["home"] == "KC"
    assert row["model_home_prob"] == 0.61
    assert row["graded"] == 0


def test_redis_grades_once_and_only_once(redis_store):
    redis_store.upsert_pregame({"event_id": "nfl:2", "league": "nfl",
                                "model_home_prob": 0.6, "model_version": "v1"})
    assert redis_store.mark_graded("nfl:2", 27, 24, 1, "now") is True
    assert redis_store.mark_graded("nfl:2", 31, 10, 1, "later") is False
    assert redis_store.get("nfl:2")["home_score"] == 27


def test_redis_freezes_the_closing_line_on_grading(redis_store):
    redis_store.upsert_pregame({"event_id": "nfl:3", "league": "nfl",
                                "model_home_prob": 0.6, "market_spread": -3.5,
                                "book_home_prob": 0.58, "model_version": "v1"})
    redis_store.mark_graded("nfl:3", 27, 24, 1, "now")
    row = redis_store.get("nfl:3")
    assert row["closing_spread"] == -3.5
    assert row["closing_home_prob"] == 0.58


def test_redis_refuses_to_rewrite_a_graded_prediction(redis_store):
    redis_store.upsert_pregame({"event_id": "nfl:4", "league": "nfl",
                                "model_home_prob": 0.60, "model_version": "v1"})
    redis_store.mark_graded("nfl:4", 27, 24, 1, "now")
    redis_store.upsert_pregame({"event_id": "nfl:4", "league": "nfl",
                                "model_home_prob": 0.99, "model_version": "v1"})
    assert redis_store.get("nfl:4")["model_home_prob"] == 0.60


def test_redis_refuses_a_cross_version_overwrite(redis_store):
    """A newer model must not rewrite a call an older one is being judged on."""
    redis_store.upsert_pregame({"event_id": "nfl:5", "league": "nfl",
                                "model_home_prob": 0.60, "model_version": "v1"})
    redis_store.upsert_pregame({"event_id": "nfl:5", "league": "nfl",
                                "model_home_prob": 0.99, "model_version": "v2"})
    assert redis_store.get("nfl:5")["model_home_prob"] == 0.60


def test_redis_allows_a_same_version_refresh_before_kickoff(redis_store):
    redis_store.upsert_pregame({"event_id": "nfl:6", "league": "nfl",
                                "model_home_prob": 0.60, "model_version": "v1"})
    redis_store.upsert_pregame({"event_id": "nfl:6", "league": "nfl",
                                "model_home_prob": 0.66, "model_version": "v1"})
    assert redis_store.get("nfl:6")["model_home_prob"] == 0.66


def test_redis_filters_rows_by_graded_state(redis_store):
    redis_store.upsert_pregame({"event_id": "a", "league": "nfl",
                                "model_home_prob": 0.5, "model_version": "v1"})
    redis_store.upsert_pregame({"event_id": "b", "league": "nfl",
                                "model_home_prob": 0.5, "model_version": "v1"})
    redis_store.mark_graded("a", 21, 17, 1, "now")
    assert redis_store.count(graded=True) == 1
    assert redis_store.count(graded=False) == 1
    assert [r["event_id"] for r in redis_store.rows(graded=True)] == ["a"]


def test_redis_clear_empties_the_index_too(redis_store):
    redis_store.upsert_pregame({"event_id": "a", "league": "nfl",
                                "model_home_prob": 0.5, "model_version": "v1"})
    redis_store.clear()
    assert redis_store.rows() == []


# ─── Configuration diagnostic ────────────────────────────────────────────────

def _clear_storage_env(monkeypatch):
    for var in ("REDIS_URL", "UPSTASH_REDIS_URL", "KV_URL", "DATABASE_URL"):
        monkeypatch.delenv(var, raising=False)


def test_report_says_nothing_is_configured(monkeypatch):
    from src.track import store
    _clear_storage_env(monkeypatch)
    report = store.config_report()
    assert report["present"] == []
    assert "Fly" in report["hint"]


def test_report_names_a_usable_variable(monkeypatch):
    from src.track import store
    _clear_storage_env(monkeypatch)
    monkeypatch.setenv("REDIS_URL", "rediss://default:tok@eu1.upstash.io:6379")
    report = store.config_report()
    assert report["present"] == ["REDIS_URL"]
    assert report["usable"] == ["REDIS_URL"]
    assert report["hint"] == ""


def test_report_flags_the_upstash_rest_url_mistake(monkeypatch):
    """The single most likely misconfiguration deserves a named diagnosis."""
    from src.track import store
    _clear_storage_env(monkeypatch)
    monkeypatch.setenv("REDIS_URL", "https://eu1-abc.upstash.io")
    report = store.config_report()
    assert report["present"] == ["REDIS_URL"]
    assert report["usable"] == []
    assert report["wrong_scheme"] == ["REDIS_URL"]
    assert "rediss://" in report["hint"]


def test_a_postgres_url_is_recognised_as_usable(monkeypatch):
    from src.track import store
    _clear_storage_env(monkeypatch)
    monkeypatch.setenv("DATABASE_URL", "postgresql://u:p@host/db")
    assert store.config_report()["usable"] == ["DATABASE_URL"]


def test_the_report_never_contains_a_secret_value(monkeypatch):
    """
    This endpoint is public. A diagnostic that echoed the URL would publish the
    database password to anyone who loaded it.
    """
    from src.track import store
    _clear_storage_env(monkeypatch)
    secret = "rediss://default:SUPERSECRETTOKEN@eu1.upstash.io:6379"
    monkeypatch.setenv("REDIS_URL", secret)
    blob = repr(store.config_report())
    assert "SUPERSECRETTOKEN" not in blob
    assert "upstash.io" not in blob
    assert secret not in blob
