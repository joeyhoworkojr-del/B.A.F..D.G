"""
The LLM behind Edge AI, behind an interface.

Edge AI is a product feature; the model that powers it is an implementation
detail. Everything above this module speaks in messages, tools and tool
results — none of it imports a vendor SDK — so moving to a different provider
means writing one class here rather than editing the assistant.

Anthropic is the initial provider. The key comes from the environment and is
read only inside this process: it is never returned by an endpoint, never
logged, and never reaches the browser.

Without a key the provider reports itself unavailable and says exactly what is
missing. It does not fall back to a canned answer — an assistant that invents
sports facts when its model is unreachable is worse than one that is honestly
switched off.
"""
from __future__ import annotations

import logging
import os
import re
from dataclasses import dataclass, field
from typing import Any, Optional, Protocol

log = logging.getLogger(__name__)

KEY_ENV_VAR = "ANTHROPIC_API_KEY"
MODEL_ENV_VAR = "EDGE_AI_MODEL"

# An organisation-level key is not scoped to a workspace, and the API refuses
# to guess which one to bill: it wants the workspace named on the request. A
# workspace-scoped key carries that already and needs nothing here. Setting
# this makes an org-level key work without anyone reissuing it.
WORKSPACE_ENV_VAR = "ANTHROPIC_WORKSPACE_ID"
WORKSPACE_HEADER = "anthropic-workspace-id"

# Haiku 4.5 is the default: the cheapest model available, and the job here is
# reading structured tool results and writing a tight paragraph rather than
# solving anything hard. Overridable by environment, so moving up to Sonnet or
# Opus is one secret and no deploy — worth doing if the answers read flat.
DEFAULT_MODEL = "claude-haiku-4-5"

# Model ids come in two shapes — a bare alias and a dated snapshot — and which
# ones an account can address is not something this code can find out without
# asking. So it asks: if the configured id comes back "not found", the next
# candidate is tried once and the one that worked is remembered for the life of
# the process.
#
# This is not a fallback to a different *tier* — every candidate here is the
# same model. It only exists so a naming difference is self-correcting instead
# of being a silent outage nobody can diagnose from the outside.
_ALIASES: dict[str, tuple[str, ...]] = {
    "claude-haiku-4-5": ("claude-haiku-4-5", "claude-haiku-4-5-20251001"),
    "claude-haiku-4-5-20251001": ("claude-haiku-4-5-20251001", "claude-haiku-4-5"),
}


def _is_missing_model(exc: Exception) -> bool:
    status = getattr(exc, "status_code", None)
    text = str(exc).lower()
    return status == 404 or "not_found" in text or (
        "model" in text and ("not found" in text or "does not exist" in text)
    )

# Long enough for a considered paragraph or two with a table, short enough that
# a runaway generation cannot run up a bill.
MAX_OUTPUT_TOKENS = 1600

REQUEST_TIMEOUT_SECONDS = 45.0


@dataclass
class LlmReply:
    """One turn from the model."""
    text: str = ""
    tool_calls: list["ToolCall"] = field(default_factory=list)
    stop_reason: str = ""
    input_tokens: int = 0
    output_tokens: int = 0
    # Input served from cache rather than charged in full. Reported so the
    # staff page can show whether caching is actually working.
    cached_tokens: int = 0

    @property
    def wants_tools(self) -> bool:
        return bool(self.tool_calls)


@dataclass
class ToolCall:
    id: str
    name: str
    arguments: dict[str, Any]


class ProviderUnavailable(RuntimeError):
    """The model could not be reached, or was never configured."""


class LlmProvider(Protocol):
    """What Edge AI needs from a model. Nothing vendor-specific appears here."""

    name: str

    def available(self) -> bool: ...

    def status(self) -> dict: ...

    async def complete(
        self,
        *,
        system: str,
        messages: list[dict],
        tools: list[dict],
    ) -> LlmReply: ...


# Anything shaped like a key, scrubbed before an error is stored or logged.
_KEYISH = re.compile(r"sk-[A-Za-z0-9_\-]{8,}")


def _describe(exc: Exception, model: str) -> str:
    """
    A diagnosable one-liner for staff. Never a credential.

    Includes the model name because the most common cause of a hard failure is
    a model id this deployment cannot use, and "not found" without saying what
    was not found sends people looking in the wrong place.
    """
    status = getattr(exc, "status_code", None)
    detail = str(exc).strip() or type(exc).__name__
    detail = _KEYISH.sub("sk-***", detail)[:300]
    prefix = f"HTTP {status}: " if status else f"{type(exc).__name__}: "
    return f"{prefix}{detail} (model: {model})"


def _user_message(exc: Exception) -> str:
    """
    What the person asking sees. Actionable where the cause is known, vague
    only where it genuinely is.
    """
    status = getattr(exc, "status_code", None)
    text = str(exc).lower()
    # Checked before the model branch: this message names a header and a
    # workspace, and the looser "model … not" test below would otherwise claim
    # it as a model problem and send whoever reads it to the wrong setting.
    if "not scoped to a workspace" in text or (status == 400 and "workspace" in text):
        return (
            "Edge AI's API key is an organisation key, which the API will not "
            "accept without being told which workspace to bill. Staff: either "
            f"set {WORKSPACE_ENV_VAR}, or issue a workspace-scoped key."
        )
    if status == 404 or "not_found" in text or "model" in text and "not" in text:
        return ("Edge AI is configured with a model this account cannot use. "
                "Staff can see the exact error on the staff page.")
    if status in (401, 403):
        return "Edge AI's API key was rejected."
    if status == 429:
        return "Edge AI is being rate limited by the provider. Try again shortly."
    if "credit" in text or "balance" in text or "billing" in text:
        return "Edge AI's account is out of credit."
    return "The assistant is temporarily unreachable."


class AnthropicProvider:
    """Claude, via the Messages API."""

    name = "anthropic"

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None,
                 workspace_id: Optional[str] = None):
        self._key = (api_key if api_key is not None else os.getenv(KEY_ENV_VAR) or "").strip()
        self._model = (model or os.getenv(MODEL_ENV_VAR) or DEFAULT_MODEL).strip()
        self._workspace = (
            workspace_id if workspace_id is not None else os.getenv(WORKSPACE_ENV_VAR) or ""
        ).strip()
        self._client = None
        self._last_error = ""

    @property
    def model(self) -> str:
        return self._model

    def available(self) -> bool:
        return bool(self._key)

    def status(self) -> dict:
        """
        Health, with no credential material in it.

        `configured` means a key is present, which is not the same as working —
        `last_error` is where a rejected key shows up.
        """
        return {
            "provider": self.name,
            "model": self._model,
            "configured": self.available(),
            "key_env_var": KEY_ENV_VAR,
            # Whether one is set, never which — a workspace id is not a secret,
            # but it is not the status endpoint's business either.
            "workspace_scoped": bool(self._workspace),
            "last_error": self._last_error,
            "note": "" if self.available() else f"set {KEY_ENV_VAR} to enable Edge AI",
        }

    def _ensure_client(self):
        if self._client is not None:
            return self._client
        if not self._key:
            raise ProviderUnavailable(f"{KEY_ENV_VAR} is not set")
        try:
            from anthropic import AsyncAnthropic
        except ImportError as exc:      # pragma: no cover - dependency is pinned
            raise ProviderUnavailable("the anthropic package is not installed") from exc
        self._client = AsyncAnthropic(
            api_key=self._key,
            timeout=REQUEST_TIMEOUT_SECONDS,
            # Sent only when configured: a workspace-scoped key already carries
            # its workspace, and naming a different one on such a key is an
            # error rather than an override.
            default_headers=(
                {WORKSPACE_HEADER: self._workspace} if self._workspace else None
            ),
        )
        return self._client

    async def complete(
        self, *, system: str, messages: list[dict], tools: list[dict],
    ) -> LlmReply:
        client = self._ensure_client()
        last: Optional[Exception] = None

        for candidate in _ALIASES.get(self._model, (self._model,)):
            try:
                response = await self._call(client, candidate, system, messages, tools)
            except Exception as exc:
                last = exc
                # Only a naming problem is worth another attempt. A rejected key
                # or an empty account fails identically on every candidate, and
                # retrying would only spend the time twice.
                if _is_missing_model(exc):
                    continue
                break
            else:
                if candidate != self._model:
                    log.info("Edge AI: %s unavailable, using %s", self._model, candidate)
                    self._model = candidate
                self._last_error = ""
                return self._to_reply(response)

        exc = last or RuntimeError("no model could be reached")
        self._last_error = _describe(exc, self._model)
        log.warning("Edge AI request failed: %s", self._last_error)
        raise ProviderUnavailable(_user_message(exc)) from exc

    async def _call(self, client, model: str, system: str,
                    messages: list[dict], tools: list[dict]):
        return await client.messages.create(
            model=model,
            max_tokens=MAX_OUTPUT_TOKENS,
            # The system prompt and the tool schemas are identical on every
            # request and every round within one, and together they are the
            # larger half of the input. Marking the end of that prefix lets the
            # repeats be read from cache at a tenth of the price.
            #
            # The breakpoint goes on the system block because the render order
            # is tools then system then messages: caching here covers both, and
            # the conversation sits after it where a change cannot invalidate
            # the prefix.
            system=[{
                "type": "text",
                "text": system,
                "cache_control": {"type": "ephemeral"},
            }],
            messages=messages,
            tools=tools or [],
        )

    @staticmethod
    def _to_reply(response) -> LlmReply:
        text_parts: list[str] = []
        calls: list[ToolCall] = []
        for block in response.content:
            kind = getattr(block, "type", "")
            if kind == "text":
                text_parts.append(block.text)
            elif kind == "tool_use":
                calls.append(ToolCall(
                    id=block.id, name=block.name, arguments=dict(block.input or {}),
                ))

        usage = getattr(response, "usage", None)
        # Cache writes and reads are billed differently from fresh input, but
        # they are all input the budget has to account for. Counting them keeps
        # the spend estimate from silently under-reporting once caching is on.
        cache_write = getattr(usage, "cache_creation_input_tokens", 0) or 0
        cache_read = getattr(usage, "cache_read_input_tokens", 0) or 0
        return LlmReply(
            text="\n".join(t for t in text_parts if t).strip(),
            tool_calls=calls,
            stop_reason=getattr(response, "stop_reason", "") or "",
            input_tokens=(getattr(usage, "input_tokens", 0) or 0) + cache_write + cache_read,
            output_tokens=getattr(usage, "output_tokens", 0) or 0,
            cached_tokens=cache_read,
        )


class UnconfiguredProvider:
    """
    Stands in when no model is configured.

    Says so rather than answering. A sports assistant that makes something up
    when its model is missing does more damage than one that is off.
    """

    name = "none"
    model = ""

    def available(self) -> bool:
        return False

    def status(self) -> dict:
        return {
            "provider": self.name,
            "model": "",
            "configured": False,
            "key_env_var": KEY_ENV_VAR,
            "workspace_scoped": False,
            "last_error": "",
            "note": f"set {KEY_ENV_VAR} to enable Edge AI",
        }

    async def complete(self, **_kwargs) -> LlmReply:
        raise ProviderUnavailable(f"{KEY_ENV_VAR} is not set")


_provider: Optional[LlmProvider] = None


def get_provider() -> LlmProvider:
    """The configured provider, or the one that admits it is not configured."""
    global _provider
    if _provider is None:
        candidate = AnthropicProvider()
        _provider = candidate if candidate.available() else UnconfiguredProvider()
    return _provider


def set_provider(provider: Optional[LlmProvider]) -> None:
    """Swap the provider — used by tests, and by any future second vendor."""
    global _provider
    _provider = provider
