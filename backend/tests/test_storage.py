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
