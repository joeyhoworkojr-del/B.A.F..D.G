"""
Edge AI — the assistant, and the rules it works under.

The shape is deliberate:

    person → StatEdge backend → controlled data functions → model → answer

The model never sees the database and never chooses what data exists. It picks
from a fixed set of functions in `context.py`, each of which returns a small
record assembled by the same code that renders the site. Everything the model
says about a game has to have come back from one of those calls.

That is enforced in three places rather than one:

  * the tool surface — there is no function that reads arbitrary data, and the
    one that reads a personal record takes its user id from the session, not
    from the model;
  * the system prompt — stated plainly, because a model that knows the rule
    follows it far more often than one left to infer it;
  * the loop — a bounded number of rounds, and an unknown tool name is refused
    rather than improvised around.

None of that makes fabrication impossible. What it does is make the honest
answer the easy one: every function returns `available: false` with a reason
when it has nothing, so "I don't have that" is always a concrete option.
"""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from typing import Any, Callable, Optional

from src.ai import context
from src.ai.provider import LlmProvider, ProviderUnavailable, get_provider

log = logging.getLogger(__name__)

# How many times the model may call tools before it has to answer. Three rounds
# is enough to look up a game, then its live state, then the news around it;
# more than that is a loop, not a question.
MAX_TOOL_ROUNDS = 4

# Questions and conversations are capped so one request cannot carry an
# unbounded prompt into a paid API call.
MAX_QUESTION_CHARS = 1000
MAX_HISTORY_TURNS = 8


SYSTEM_PROMPT = """\
You are Edge AI, the sports intelligence assistant inside StatEdge — a football \
prediction platform covering the NFL and college football.

How you speak: analytical, calm, concise. Confident where the data supports it \
and plain about where it does not. You are willing to disagree with the model, \
with the market, or with the person asking, and you say why. No hype, no \
guaranteed winners, no betting-tout register. Two or three short paragraphs is \
usually the right length; use a list only when the content is genuinely a list.

What you may state as fact:

You have tools that return StatEdge's own data. EVERY score, line, spread, \
total, probability, projection, statistic, headline, community percentage and \
analyst record you mention MUST have come back from a tool call in this \
conversation. You have no other source. Your training data is years out of \
date on every one of these and must never be used for them.

If a tool returns `available: false`, that means StatEdge does not have the \
information — say so plainly and give the reason it returned. Never fill the \
gap from memory, never estimate a number to be helpful, and never describe a \
game situation the feed did not report. "I don't have that" is a good answer. \
Inventing one is not.

Two distinctions to keep straight:

  * The pre-game projection is frozen at kickoff and is what StatEdge's public \
    record grades. The live projection moves with the game and is never graded. \
    Do not present one as the other.
  * A historical hit rate is not a predicted probability, and a community split \
    is how StatEdge users picked — not a betting handle or a market share.

On live games: StatEdge's live model reads down, distance and field position, \
so the probability moves during a drive rather than only after a score. When \
someone asks why a number moved, use `get_live_game_state` and explain the \
actual game state that caused it. If `uses_field_position` is false, the \
projection is running on score and clock alone — say that rather than inventing \
a situation.

You may explain what the model weighed and what its recorded inputs were. You \
may not invent a causal story. If you do not know why the model landed where it \
did, say the model does not publish that.

Nothing you say is betting advice, and saving a pick on StatEdge does not place \
a wager. Do not tell anyone what to bet or how much.\
"""


# The tool surface. Each entry maps to a function in context.py and nothing
# else; there is no generic query tool and no way to add one at runtime.
TOOLS: list[dict] = [
    {
        "name": "get_game_context",
        "description": (
            "Teams, status, score, the model's pre-game projection, the market "
            "line and any edges for one game. Start here for any question about "
            "a specific matchup."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "league": {"type": "string", "enum": list(context.LEAGUES)},
                "event_id": {"type": "string", "description": "The game's id."},
            },
            "required": ["league", "event_id"],
        },
    },
    {
        "name": "get_live_game_state",
        "description": (
            "For a game in progress: the score, clock, possession, down, "
            "distance and field position, the live win probability, and the "
            "reason the projection last moved. Use this for 'what changed' and "
            "'why did the probability move'."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "league": {"type": "string", "enum": list(context.LEAGUES)},
                "event_id": {"type": "string"},
            },
            "required": ["league", "event_id"],
        },
    },
    {
        "name": "get_prediction",
        "description": (
            "The model's pre-game call and its live call for one game, reported "
            "separately. Use when asked what StatEdge thinks."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "league": {"type": "string", "enum": list(context.LEAGUES)},
                "event_id": {"type": "string"},
            },
            "required": ["league", "event_id"],
        },
    },
    {
        "name": "get_todays_games",
        "description": (
            "Every game on today's board with its model probability and line. "
            "Use for 'what should I watch' and to find a game's id from team "
            "names."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "league": {"type": "string", "enum": list(context.LEAGUES),
                           "description": "Omit for both leagues."},
            },
        },
    },
    {
        "name": "get_player_props",
        "description": "Projected player numbers for one game, with the season averages behind them.",
        "input_schema": {
            "type": "object",
            "properties": {
                "league": {"type": "string", "enum": list(context.LEAGUES)},
                "event_id": {"type": "string"},
            },
            "required": ["league", "event_id"],
        },
    },
    {
        "name": "get_news",
        "description": (
            "Recent headlines with summaries and publishers. Summarise and "
            "attribute; do not reproduce articles."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "league": {"type": "string", "enum": list(context.LEAGUES)},
            },
        },
    },
    {
        "name": "get_community_consensus",
        "description": "How StatEdge users have picked one game.",
        "input_schema": {
            "type": "object",
            "properties": {
                "league": {"type": "string", "enum": list(context.LEAGUES)},
                "event_id": {"type": "string"},
            },
            "required": ["league", "event_id"],
        },
    },
    {
        "name": "get_leaderboard",
        "description": "Ranked StatEdge analysts by Edge Rating, with provisional ones marked.",
        "input_schema": {
            "type": "object",
            "properties": {
                "league": {"type": "string", "enum": list(context.LEAGUES)},
            },
        },
    },
    {
        "name": "get_user_performance",
        "description": (
            "The record of the person you are talking to: their graded picks, "
            "units and recent history. Takes no arguments — it always refers to "
            "the signed-in user and cannot read anyone else's account."
        ),
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "get_analyst_profile",
        "description": "One analyst's public profile and verified record.",
        "input_schema": {
            "type": "object",
            "properties": {"username": {"type": "string"}},
            "required": ["username"],
        },
    },
]

TOOL_NAMES = {t["name"] for t in TOOLS}


@dataclass
class AskContext:
    """
    Who is asking and what they are looking at.

    `user_id` comes from the session and is the only way a personal record can
    be reached — the model cannot name a user.
    """
    user_id: Optional[str] = None
    league: Optional[str] = None
    event_id: Optional[str] = None


@dataclass
class Answer:
    text: str = ""
    tools_used: list[str] = field(default_factory=list)
    rounds: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    truncated: bool = False


def _dispatch(ctx: AskContext) -> dict[str, Callable]:
    """
    Bind tool names to functions, closing the user id over the session.

    `get_user_performance` takes no arguments from the model on purpose: the id
    is supplied here, so there is nothing to point at another account.
    """
    return {
        "get_game_context": context.get_game_context,
        "get_live_game_state": context.get_live_game_state,
        "get_prediction": context.get_prediction,
        "get_todays_games": context.get_todays_games,
        "get_player_props": context.get_player_props,
        "get_news": context.get_news,
        "get_community_consensus": context.get_community_consensus,
        "get_leaderboard": context.get_leaderboard,
        "get_user_performance": lambda **_: context.get_user_performance(ctx.user_id),
        "get_analyst_profile": context.get_analyst_profile,
    }


async def _run_tool(name: str, arguments: dict, ctx: AskContext) -> dict:
    """
    Call one tool.

    An unknown name is refused rather than guessed at, and a raising tool comes
    back as unavailable — a broken lookup must not become an invented answer.
    """
    if name not in TOOL_NAMES:
        return {"available": False, "what": name, "reason": "no such tool"}
    try:
        return await _dispatch(ctx)[name](**(arguments or {}))
    except TypeError as exc:
        return {"available": False, "what": name, "reason": f"bad arguments: {exc}"}
    except Exception as exc:
        log.warning("Edge AI tool %s failed: %s", name, type(exc).__name__)
        return {"available": False, "what": name,
                "reason": "that lookup failed; the data is not available right now"}


def _opening_context(ctx: AskContext) -> str:
    """
    Tell the model what the person is looking at.

    This is what makes "why did we move to 64%" answerable without naming the
    teams: the game on screen travels with the question.
    """
    if ctx.league and ctx.event_id:
        return (
            f"\n\nThe person is currently viewing a {ctx.league.upper()} game, "
            f"event id {ctx.event_id}. When they say 'this game', 'they', or "
            f"'we', they mean that one. Look it up rather than asking which."
        )
    return ""


async def ask(
    question: str,
    ctx: Optional[AskContext] = None,
    history: Optional[list[dict]] = None,
    provider: Optional[LlmProvider] = None,
) -> Answer:
    """
    Answer one question.

    Raises ProviderUnavailable when no model is configured or reachable. The
    caller reports that as a configuration state; it never becomes a fabricated
    reply.
    """
    ctx = ctx or AskContext()
    provider = provider or get_provider()
    if not provider.available():
        raise ProviderUnavailable("Edge AI is not configured")

    question = (question or "").strip()[:MAX_QUESTION_CHARS]
    if not question:
        raise ValueError("Ask a question.")

    messages: list[dict] = []
    for turn in (history or [])[-MAX_HISTORY_TURNS:]:
        role = turn.get("role")
        text = str(turn.get("content") or "")[:MAX_QUESTION_CHARS]
        if role in ("user", "assistant") and text:
            messages.append({"role": role, "content": text})
    messages.append({"role": "user", "content": question})

    system = SYSTEM_PROMPT + _opening_context(ctx)
    answer = Answer()

    for round_index in range(MAX_TOOL_ROUNDS):
        reply = await provider.complete(system=system, messages=messages, tools=TOOLS)
        answer.rounds = round_index + 1
        answer.input_tokens += reply.input_tokens
        answer.output_tokens += reply.output_tokens

        if not reply.wants_tools:
            answer.text = reply.text
            return answer

        messages.append({
            "role": "assistant",
            "content": (
                ([{"type": "text", "text": reply.text}] if reply.text else [])
                + [
                    {"type": "tool_use", "id": call.id, "name": call.name,
                     "input": call.arguments}
                    for call in reply.tool_calls
                ]
            ),
        })

        results = []
        for call in reply.tool_calls:
            answer.tools_used.append(call.name)
            payload = await _run_tool(call.name, call.arguments, ctx)
            results.append({
                "type": "tool_result",
                "tool_use_id": call.id,
                "content": json.dumps(payload, default=str),
            })
        messages.append({"role": "user", "content": results})

    # Out of rounds. Ask for the answer with the tools withdrawn, so the reply
    # is written from what was already looked up rather than from more calls.
    final = await provider.complete(system=system, messages=messages, tools=[])
    answer.text = final.text
    answer.input_tokens += final.input_tokens
    answer.output_tokens += final.output_tokens
    answer.truncated = True
    return answer


def status() -> dict:
    """What Edge AI is, and whether it can run. No credentials, ever."""
    provider = get_provider()
    report = provider.status()
    return {
        **report,
        "available": provider.available(),
        "tools": sorted(TOOL_NAMES),
        "max_tool_rounds": MAX_TOOL_ROUNDS,
    }
