"""
Staff portal.

Read-mostly by design. Everything here is operational visibility — who signed
up, what has been published, whether storage is healthy — rather than levers
that can rewrite history. Deliberately absent: any way to edit or delete a
graded pick. A staff tool that could quietly change a result would undermine
the one claim the product makes.

Admin is granted by the ADMIN_USERNAMES environment variable, so it cannot be
obtained by anything that can write to the database.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends

from src.accounts.models import COLLECTION as USERS, User
from src.api.routes.auth import require_admin
from src.picks import leaderboard, service as picks
from src.store.documents import get_docs
from src.track import ledger

router = APIRouter()


@router.get("/admin/overview", tags=["Admin"])
async def overview(admin: User = Depends(require_admin)) -> dict:
    """Everything a staff member needs at a glance."""
    users = get_docs().list(USERS)
    all_picks = picks.all_picks()
    graded = [p for p in all_picks if p.graded]
    open_picks = [p for p in all_picks if not p.graded]

    return {
        "storage": {
            "backend": ledger.storage_backend(),
            "durable": ledger.storage_durable(),
        },
        "accounts": {
            "total": len(users),
            "onboarded": sum(1 for u in users if u.get("onboarded")),
            "founding": sum(1 for u in users if "founding_analyst" in (u.get("badges") or [])),
            "by_level": _count(users, "level"),
        },
        "picks": {
            "total": len(all_picks),
            "open": len(open_picks),
            "graded": len(graded),
            "by_market": _count([p.to_doc() for p in all_picks], "market"),
            "by_result": _count([p.to_doc() for p in graded], "result"),
            "by_league": _count([p.to_doc() for p in all_picks], "league"),
        },
        "model_record": {
            "graded": ledger.accuracy_summary()["overall"]["games_graded"],
            "pending": ledger.accuracy_summary()["pending"],
        },
        "leaderboard_size": len(leaderboard.standings()),
    }


@router.get("/admin/users", tags=["Admin"])
async def list_users(limit: int = 100, admin: User = Depends(require_admin)) -> dict:
    """
    Registered accounts, newest first.

    Emails are included because staff need them to answer a support request,
    but nothing that could authenticate as the user ever leaves the server: the
    password hash is dropped here rather than merely hidden in the UI.
    """
    users = get_docs().list(USERS)
    users.sort(key=lambda u: u.get("created_at") or "", reverse=True)
    return {
        "count": len(users),
        "users": [
            {
                "id": u.get("id"), "username": u.get("username"),
                "email": u.get("email"), "display_name": u.get("display_name"),
                "level": u.get("level"), "badges": u.get("badges") or [],
                "onboarded": u.get("onboarded"), "created_at": u.get("created_at"),
                "picks": sum(1 for p in picks.all_picks() if p.user_id == u.get("id")),
            }
            for u in users[:max(1, min(limit, 500))]
        ],
    }


@router.get("/admin/picks", tags=["Admin"])
async def list_picks(limit: int = 100, admin: User = Depends(require_admin)) -> dict:
    """Every published pick, newest first — for inspection, not editing."""
    rows = picks.all_picks()
    rows.sort(key=lambda p: p.created_at, reverse=True)
    return {
        "count": len(rows),
        "picks": [p.to_public() for p in rows[:max(1, min(limit, 500))]],
    }


def _count(rows: list[dict], field: str) -> dict[str, int]:
    out: dict[str, int] = {}
    for row in rows:
        key = str(row.get(field) or "unknown")
        out[key] = out.get(key, 0) + 1
    return dict(sorted(out.items()))
