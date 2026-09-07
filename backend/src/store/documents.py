"""
A small document store, on whichever backend the ledger is already using.

The prediction ledger proved the pattern: this application does its logic in
Python and needs storage to hold documents and look them up by id or by one
indexed field. Rather than introduce a second database technology for accounts
and picks, this generalises the same three backends the ledger runs on —
Redis/Upstash, Postgres, SQLite — so new domain models inherit the durability
that is already configured and deployed.

Deliberately narrow. This is not an ORM and does not try to be: no joins, no
migrations per model, no query language. Collections hold JSON documents,
addressed by id, with optional unique indexes for lookups like username and
email. Anything needing real relational queries should move to Postgres tables
rather than growing this file.
"""
from __future__ import annotations

import json
import logging
import threading
from typing import Any, Iterable, Optional

from src.track import db, store as ledger_store

log = logging.getLogger(__name__)

_LOCK = threading.Lock()

_SCHEMA = """
CREATE TABLE IF NOT EXISTS documents (
    collection TEXT NOT NULL,
    doc_id     TEXT NOT NULL,
    data       TEXT NOT NULL,
    PRIMARY KEY (collection, doc_id)
);
"""

_INDEX_SCHEMA = """
CREATE TABLE IF NOT EXISTS document_index (
    collection TEXT NOT NULL,
    field      TEXT NOT NULL,
    value      TEXT NOT NULL,
    doc_id     TEXT NOT NULL,
    PRIMARY KEY (collection, field, value)
);
"""

_PREFIX = "se"


class UniqueViolation(Exception):
    """An indexed value is already taken — a username or email collision."""


# ─── Redis ───────────────────────────────────────────────────────────────────

class _RedisDocs:
    backend = "redis"

    def __init__(self, client):
        self._r = client

    def _key(self, collection: str, doc_id: str) -> str:
        return f"{_PREFIX}:{collection}:{doc_id}"

    def _ids(self, collection: str) -> str:
        return f"{_PREFIX}:{collection}:__ids"

    def _ix(self, collection: str, field: str, value: str) -> str:
        return f"{_PREFIX}:{collection}:__ix:{field}:{value.lower()}"

    def put(self, collection, doc_id, doc, indexes=None):
        indexes = indexes or {}
        # Claim every index before writing, so a half-registered user cannot
        # exist: SETNX fails if another account already holds the value.
        claimed: list[str] = []
        for field, value in indexes.items():
            if value is None:
                continue
            key = self._ix(collection, field, str(value))
            if not self._r.set(key, doc_id, nx=True):
                if self._r.get(key) != doc_id:
                    for c in claimed:
                        self._r.delete(c)
                    raise UniqueViolation(f"{field} is already taken")
            claimed.append(key)
        self._r.set(self._key(collection, doc_id), json.dumps(doc))
        self._r.sadd(self._ids(collection), doc_id)

    def get(self, collection, doc_id):
        raw = self._r.get(self._key(collection, doc_id))
        return json.loads(raw) if raw else None

    def find(self, collection, field, value):
        doc_id = self._r.get(self._ix(collection, field, str(value)))
        return self.get(collection, doc_id) if doc_id else None

    def list(self, collection, limit=None):
        ids = sorted(self._r.smembers(self._ids(collection)) or [])
        if not ids:
            return []
        if limit is not None:
            ids = ids[:limit]
        raws = self._r.mget([self._key(collection, i) for i in ids])
        return [json.loads(r) for r in raws if r]

    def delete(self, collection, doc_id, indexes=None):
        for field, value in (indexes or {}).items():
            if value is not None:
                self._r.delete(self._ix(collection, field, str(value)))
        self._r.delete(self._key(collection, doc_id))
        self._r.srem(self._ids(collection), doc_id)


# ─── SQL ─────────────────────────────────────────────────────────────────────

class _SqlDocs:
    backend = "sql"

    def _connect(self):
        conn = db.connect(_SCHEMA, [], "documents")
        conn.execute(_INDEX_SCHEMA)
        return conn

    def put(self, collection, doc_id, doc, indexes=None):
        with self._connect() as conn:
            for field, value in (indexes or {}).items():
                if value is None:
                    continue
                row = conn.execute(
                    "SELECT doc_id FROM document_index "
                    "WHERE collection = ? AND field = ? AND value = ?",
                    (collection, field, str(value).lower()),
                ).fetchone()
                if row and row["doc_id"] != doc_id:
                    raise UniqueViolation(f"{field} is already taken")
            conn.execute(
                "INSERT INTO documents (collection, doc_id, data) VALUES (?, ?, ?) "
                "ON CONFLICT(collection, doc_id) DO UPDATE SET data = excluded.data",
                (collection, doc_id, json.dumps(doc)),
            )
            for field, value in (indexes or {}).items():
                if value is None:
                    continue
                conn.execute(
                    "INSERT INTO document_index (collection, field, value, doc_id) "
                    "VALUES (?, ?, ?, ?) ON CONFLICT(collection, field, value) "
                    "DO UPDATE SET doc_id = excluded.doc_id",
                    (collection, field, str(value).lower(), doc_id),
                )

    def get(self, collection, doc_id):
        with self._connect() as conn:
            row = conn.execute(
                "SELECT data FROM documents WHERE collection = ? AND doc_id = ?",
                (collection, doc_id),
            ).fetchone()
            return json.loads(row["data"]) if row else None

    def find(self, collection, field, value):
        with self._connect() as conn:
            row = conn.execute(
                "SELECT doc_id FROM document_index "
                "WHERE collection = ? AND field = ? AND value = ?",
                (collection, field, str(value).lower()),
            ).fetchone()
        return self.get(collection, row["doc_id"]) if row else None

    def list(self, collection, limit=None):
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT data FROM documents WHERE collection = ?", (collection,),
            ).fetchall()
        docs = [json.loads(r["data"]) for r in rows]
        return docs[:limit] if limit is not None else docs

    def delete(self, collection, doc_id, indexes=None):
        with self._connect() as conn:
            for field, value in (indexes or {}).items():
                if value is not None:
                    conn.execute(
                        "DELETE FROM document_index "
                        "WHERE collection = ? AND field = ? AND value = ?",
                        (collection, field, str(value).lower()),
                    )
            conn.execute(
                "DELETE FROM documents WHERE collection = ? AND doc_id = ?",
                (collection, doc_id),
            )


_docs = None


def get_docs():
    """The document store, on the same backend the ledger resolved to."""
    global _docs
    if _docs is None:
        with _LOCK:
            if _docs is None:
                if ledger_store.redis_url():
                    try:
                        client = ledger_store.RedisStore()._redis()
                        client.ping()
                        _docs = _RedisDocs(client)
                    except Exception as exc:
                        log.error("documents: Redis unusable, using SQL: %s",
                                  ledger_store._scrub(exc))
                        _docs = _SqlDocs()
                else:
                    _docs = _SqlDocs()
    return _docs


def reset_docs() -> None:
    """Test seam: forget the resolved backend."""
    global _docs
    _docs = None
