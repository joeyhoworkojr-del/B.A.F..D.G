"""
The Redis document store — the backend that actually runs in production.

Every other account and pick test forces SQLite, which left the deployed path
untested. These run the same flows against the Redis implementation.
"""
from __future__ import annotations

import pytest

from src.store.documents import UniqueViolation, _RedisDocs


class FakeRedis:
    """The subset of Redis the document store uses, with redis-py's semantics."""

    def __init__(self):
        self.kv: dict[str, str] = {}
        self.sets: dict[str, set[str]] = {}

    def set(self, key, value, nx=False):
        # redis-py returns None (not False) when NX fails.
        if nx and key in self.kv:
            return None
        self.kv[key] = value
        return True

    def get(self, key):
        return self.kv.get(key)

    def delete(self, *keys):
        for k in keys:
            self.kv.pop(k, None)
            self.sets.pop(k, None)

    def sadd(self, key, *values):
        self.sets.setdefault(key, set()).update(values)

    def srem(self, key, *values):
        self.sets.get(key, set()).difference_update(values)

    def smembers(self, key):
        return set(self.sets.get(key, set()))

    def mget(self, keys):
        return [self.kv.get(k) for k in keys]

    def ping(self):
        return True


@pytest.fixture
def docs():
    return _RedisDocs(FakeRedis())


def test_a_document_round_trips(docs):
    docs.put("users", "u1", {"id": "u1", "username": "joey"})
    assert docs.get("users", "u1")["username"] == "joey"


def test_a_missing_document_is_none(docs):
    assert docs.get("users", "nope") is None


def test_an_indexed_lookup_finds_the_document(docs):
    docs.put("users", "u1", {"id": "u1", "username": "joey"},
             indexes={"username": "joey", "email": "j@e.com"})
    assert docs.find("users", "username", "joey")["id"] == "u1"
    assert docs.find("users", "email", "j@e.com")["id"] == "u1"


def test_index_lookups_are_case_insensitive(docs):
    docs.put("users", "u1", {"id": "u1"}, indexes={"email": "Joey@Example.com"})
    assert docs.find("users", "email", "joey@example.com") is not None


def test_a_taken_index_is_refused(docs):
    docs.put("users", "u1", {"id": "u1"}, indexes={"username": "joey"})
    with pytest.raises(UniqueViolation):
        docs.put("users", "u2", {"id": "u2"}, indexes={"username": "joey"})


def test_a_rejected_write_does_not_leave_a_half_claimed_index(docs):
    """
    The failure that would matter: a second index claimed before the collision
    is found would permanently reserve an email for an account never created.
    """
    docs.put("users", "u1", {"id": "u1"}, indexes={"username": "joey"})
    with pytest.raises(UniqueViolation):
        docs.put("users", "u2", {"id": "u2"},
                 indexes={"email": "new@e.com", "username": "joey"})
    # The email must still be free for a later, valid registration.
    docs.put("users", "u3", {"id": "u3"}, indexes={"email": "new@e.com"})
    assert docs.find("users", "email", "new@e.com")["id"] == "u3"


def test_the_owner_can_rewrite_its_own_indexed_document(docs):
    """A profile update re-puts the same indexes and must not self-collide."""
    docs.put("users", "u1", {"id": "u1", "bio": ""}, indexes={"username": "joey"})
    docs.put("users", "u1", {"id": "u1", "bio": "analyst"}, indexes={"username": "joey"})
    assert docs.get("users", "u1")["bio"] == "analyst"


def test_listing_returns_every_document(docs):
    for i in range(3):
        docs.put("picks", f"p{i}", {"id": f"p{i}"})
    assert len(docs.list("picks")) == 3


def test_listing_an_empty_collection_is_empty(docs):
    assert docs.list("picks") == []


def test_collections_do_not_leak_into_each_other(docs):
    docs.put("users", "x", {"id": "x"})
    docs.put("picks", "x", {"id": "x", "kind": "pick"})
    assert docs.get("picks", "x")["kind"] == "pick"
    assert "kind" not in docs.get("users", "x")
    assert len(docs.list("users")) == 1


def test_deleting_releases_the_index(docs):
    docs.put("users", "u1", {"id": "u1"}, indexes={"username": "joey"})
    docs.delete("users", "u1", indexes={"username": "joey"})
    assert docs.get("users", "u1") is None
    assert docs.find("users", "username", "joey") is None
    docs.put("users", "u2", {"id": "u2"}, indexes={"username": "joey"})
    assert docs.find("users", "username", "joey")["id"] == "u2"


def test_a_deleted_document_leaves_the_listing(docs):
    docs.put("picks", "p1", {"id": "p1"})
    docs.delete("picks", "p1")
    assert docs.list("picks") == []


def test_a_none_index_value_is_skipped(docs):
    docs.put("users", "u1", {"id": "u1"}, indexes={"username": "joey", "email": None})
    assert docs.find("users", "username", "joey") is not None
