"""
Where chat messages live.

Redis when it is configured, an in-memory ring otherwise. Messages are the one
part of this feature that can survive being lost — a room for a game in
progress is ephemeral by nature, and nothing graded or published depends on it.
Moderation state is the opposite and lives in the durable document store; see
moderation.py.

Reads are by cursor. A client asks for everything after the sequence number it
already has, so the common case — a room that has been open for an hour with
nothing new — costs one integer comparison and returns nothing. That is what
keeps this off the "poll the whole database every second" path.

Each room is capped. A blowout game with thousands of messages keeps the most
recent window and drops the rest; the alternative is unbounded growth on a
512 MB machine.
"""
from __future__ import annotations

import json
import logging
import threading
from collections import deque
from typing import Optional

from src.chat.models import Message

log = logging.getLogger(__name__)

# Enough to scroll back through a game, few enough that a hundred rooms fit in
# memory comfortably.
MAX_PER_ROOM = 500

# How many rooms the in-memory fallback holds before evicting the least
# recently written. Redis has its own expiry instead.
MAX_ROOMS = 120

# Rooms disappear a day after the game does. Nobody returns to last Tuesday's
# chat, and an unbounded key space is a slow leak.
ROOM_TTL_SECONDS = 36 * 3600

_PREFIX = "se:chat"
_LOCK = threading.Lock()


class _MemoryRooms:
    """The fallback. Correct, bounded, and lost on restart."""

    backend = "memory"

    def __init__(self) -> None:
        self._rooms: dict[str, deque[Message]] = {}
        self._seq: dict[str, int] = {}
        self._order: deque[str] = deque()

    def _room(self, game_id: str) -> deque[Message]:
        room = self._rooms.get(game_id)
        if room is None:
            if len(self._rooms) >= MAX_ROOMS:
                oldest = self._order.popleft() if self._order else None
                if oldest is not None:
                    self._rooms.pop(oldest, None)
                    self._seq.pop(oldest, None)
            room = self._rooms[game_id] = deque(maxlen=MAX_PER_ROOM)
            self._order.append(game_id)
        return room

    def append(self, message: Message) -> Message:
        with _LOCK:
            room = self._room(message.game_id)
            self._seq[message.game_id] = self._seq.get(message.game_id, 0) + 1
            message.seq = self._seq[message.game_id]
            room.append(message)
            return message

    def since(self, game_id: str, after: int, limit: int) -> list[Message]:
        with _LOCK:
            room = self._rooms.get(game_id)
            if not room:
                return []
            return [m for m in room if m.seq > after][:limit]

    def latest(self, game_id: str, limit: int) -> list[Message]:
        with _LOCK:
            room = self._rooms.get(game_id)
            return list(room)[-limit:] if room else []

    def get(self, game_id: str, message_id: str) -> Optional[Message]:
        with _LOCK:
            room = self._rooms.get(game_id) or ()
            return next((m for m in room if m.id == message_id), None)

    def replace(self, message: Message) -> None:
        with _LOCK:
            room = self._rooms.get(message.game_id)
            if not room:
                return
            for i, existing in enumerate(room):
                if existing.id == message.id:
                    room[i] = message
                    return

    def count(self, game_id: str) -> int:
        with _LOCK:
            return len(self._rooms.get(game_id) or ())

    def clear(self) -> None:
        with _LOCK:
            self._rooms.clear()
            self._seq.clear()
            self._order.clear()


class _RedisRooms:
    """
    A list per room, plus a counter for the cursor.

    A list rather than a stream: the operations needed are append, read a tail,
    and rewrite one entry in place for reactions and deletions. Streams do not
    do the last one, and the rewrite is what keeps a deleted message's place in
    the sequence rather than renumbering everyone after it.
    """

    backend = "redis"

    def __init__(self, client) -> None:
        self._r = client

    def _key(self, game_id: str) -> str:
        return f"{_PREFIX}:room:{game_id}"

    def _seq_key(self, game_id: str) -> str:
        return f"{_PREFIX}:seq:{game_id}"

    def append(self, message: Message) -> Message:
        key, seq_key = self._key(message.game_id), self._seq_key(message.game_id)
        message.seq = int(self._r.incr(seq_key))
        pipe = self._r.pipeline()
        pipe.rpush(key, json.dumps(message.to_doc()))
        pipe.ltrim(key, -MAX_PER_ROOM, -1)
        pipe.expire(key, ROOM_TTL_SECONDS)
        pipe.expire(seq_key, ROOM_TTL_SECONDS)
        pipe.execute()
        return message

    def _all(self, game_id: str) -> list[Message]:
        raw = self._r.lrange(self._key(game_id), 0, -1) or []
        out = []
        for item in raw:
            try:
                out.append(Message.from_doc(json.loads(item)))
            except Exception:
                # One unreadable row must not take the room down with it.
                continue
        return out

    def since(self, game_id: str, after: int, limit: int) -> list[Message]:
        return [m for m in self._all(game_id) if m.seq > after][:limit]

    def latest(self, game_id: str, limit: int) -> list[Message]:
        raw = self._r.lrange(self._key(game_id), -limit, -1) or []
        out = []
        for item in raw:
            try:
                out.append(Message.from_doc(json.loads(item)))
            except Exception:
                continue
        return out

    def get(self, game_id: str, message_id: str) -> Optional[Message]:
        return next((m for m in self._all(game_id) if m.id == message_id), None)

    def replace(self, message: Message) -> None:
        key = self._key(message.game_id)
        for index, item in enumerate(self._r.lrange(key, 0, -1) or []):
            try:
                if json.loads(item).get("id") == message.id:
                    self._r.lset(key, index, json.dumps(message.to_doc()))
                    return
            except Exception:
                continue

    def count(self, game_id: str) -> int:
        return int(self._r.llen(self._key(game_id)) or 0)

    def clear(self) -> None:
        for key in self._r.scan_iter(f"{_PREFIX}:*"):
            self._r.delete(key)


_rooms = None


def get_rooms():
    """The room store, on whichever backend is configured."""
    global _rooms
    if _rooms is not None:
        return _rooms
    from src.track import store as ledger_store
    if ledger_store.redis_url():
        try:
            import redis
            client = redis.from_url(ledger_store.redis_url(), decode_responses=True)
            client.ping()
            _rooms = _RedisRooms(client)
            return _rooms
        except Exception as exc:
            log.error("chat: Redis unusable, using memory: %s", ledger_store._scrub(exc))
    _rooms = _MemoryRooms()
    return _rooms


def reset_rooms() -> None:
    """Test seam: forget the resolved backend."""
    global _rooms
    if _rooms is not None:
        try:
            _rooms.clear()
        except Exception:
            pass
    _rooms = None
