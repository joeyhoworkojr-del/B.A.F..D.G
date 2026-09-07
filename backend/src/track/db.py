"""
Storage backend for the ledger.

SQLite by default, Postgres when DATABASE_URL is set. The ledger's SQL is
portable — a TEXT primary key, no AUTOINCREMENT, and an ON CONFLICT upsert both
engines support — so this module only has to reconcile three differences:

  * parameter style: SQLite takes "?", psycopg2 takes "%s"
  * row access: sqlite3.Row vs a dict cursor
  * introspection for migrations: PRAGMA vs information_schema

Why it matters: on Fly the container's disk is replaced on every deploy, so a
SQLite ledger silently starts over each release. Pointing DATABASE_URL at a
managed Postgres is what makes the track record survive, and nothing above this
module has to change for that to happen.
"""
from __future__ import annotations

import logging
import os
import sqlite3
import threading
from typing import Any, Iterable, Optional

log = logging.getLogger(__name__)

# Held by the ledger around every access, so a single shared Postgres
# connection is safe to reuse rather than reconnecting per statement.
_PG_LOCK = threading.Lock()
_pg_conn = None


def clean_url(raw: str) -> str:
    """
    Trim a pasted connection string.

    A value copied out of a shell command arrives wrapped in the quotes that
    were shell syntax, not part of the URL. Stripping them turns a silent
    connection failure into a working config.
    """
    url = (raw or "").strip()
    for q in ("'", '"'):
        if len(url) >= 2 and url.startswith(q) and url.endswith(q):
            url = url[1:-1].strip()
    return url


def database_url() -> str:
    """The configured Postgres URL, or "" when running on SQLite."""
    url = clean_url(os.getenv("DATABASE_URL"))
    # A URL pointing at a host that isn't provisioned is worse than no URL at
    # all: it would fail every write. Only schemes we can actually open count.
    if url.startswith(("postgres://", "postgresql://")):
        return url
    return ""


def is_postgres() -> bool:
    return bool(database_url())


def backend_name() -> str:
    return "postgres" if is_postgres() else "sqlite"


def sqlite_path() -> str:
    """
    Resolve the SQLite path, guaranteeing it is writable. If the configured
    directory can't be created or written (e.g. a volume didn't mount), fall
    back to a local file so the API never 500s over storage.
    """
    path = os.getenv("LEDGER_PATH", "ledger.db")
    parent = os.path.dirname(path)
    try:
        if parent:
            os.makedirs(parent, exist_ok=True)
        if not os.access(parent or ".", os.W_OK):
            raise OSError(f"{parent!r} not writable")
        return path
    except OSError:
        return "ledger.db"      # ephemeral fallback — better than a hard failure


def to_pg_params(sql: str) -> str:
    """
    Rewrite "?" placeholders to "%s", leaving quoted text alone.

    Naive replacement would corrupt any literal containing a question mark, so
    this walks the string and tracks whether it is inside a quote.
    """
    out: list[str] = []
    quote: Optional[str] = None
    for ch in sql:
        if quote:
            if ch == quote:
                quote = None
            out.append(ch)
        elif ch in ("'", '"'):
            quote = ch
            out.append(ch)
        elif ch == "?":
            out.append("%s")
        else:
            out.append(ch)
    return "".join(out)


class _PgConnection:
    """Presents the small slice of the sqlite3 connection API the ledger uses."""

    def __init__(self, raw):
        self._raw = raw

    def execute(self, sql: str, params: Iterable[Any] = ()):
        from psycopg2.extras import RealDictCursor
        cur = self._raw.cursor(cursor_factory=RealDictCursor)
        cur.execute(to_pg_params(sql), tuple(params))
        return cur

    def executescript(self, sql: str):
        cur = self._raw.cursor()
        cur.execute(sql)
        return cur

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        if exc_type is None:
            self._raw.commit()
        else:
            self._raw.rollback()
        return False       # never swallow the caller's exception


def _pg_connect():
    """One shared Postgres connection, reopened if it has gone away."""
    global _pg_conn
    import psycopg2

    with _PG_LOCK:
        if _pg_conn is not None and getattr(_pg_conn, "closed", 1) == 0:
            return _pg_conn
        _pg_conn = psycopg2.connect(database_url())
        return _pg_conn


def _existing_columns(conn, table: str) -> set[str]:
    """Column names already on `table`, for the additive migration step."""
    if is_postgres():
        rows = conn.execute(
            "SELECT column_name AS name FROM information_schema.columns "
            "WHERE table_name = ?",
            (table,),
        ).fetchall()
    else:
        rows = conn.execute(f"PRAGMA table_info({table})").fetchall()
    return {r["name"] for r in rows}


def connect(schema: str, migrations: list[tuple[str, str]], table: str):
    """
    Open a connection with the schema applied and any missing columns added.

    Returns a context manager that commits on success and rolls back on error.
    """
    if is_postgres():
        conn = _PgConnection(_pg_connect())
        # Postgres has no "REAL"/"INTEGER" incompatibility with these DDLs, so
        # the same schema string runs on both engines.
        conn.executescript(schema)
        conn._raw.commit()
    else:
        raw = sqlite3.connect(sqlite_path())
        raw.row_factory = sqlite3.Row
        raw.execute(schema)
        conn = raw

    existing = _existing_columns(conn, table)
    for col, decl in migrations:
        if col not in existing:
            try:
                conn.execute(f"ALTER TABLE {table} ADD COLUMN {col} {decl}")
            except Exception as exc:      # already added by a concurrent worker
                log.debug("migration for %s.%s skipped: %s", table, col, exc)
    if is_postgres():
        conn._raw.commit()
    return conn
