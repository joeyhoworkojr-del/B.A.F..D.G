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
from dataclasses import dataclass, field
from typing import Any, Optional, Protocol

log = logging.getLogger(__name__)

KEY_ENV_VAR = "ANTHROPIC_API_KEY"
MODEL_ENV_VAR = "EDGE_AI_MODEL"

# Opus 5 is the default. Overridable by environment so the model can be changed
# without a code deploy — including to a cheaper one if volume warrants it.
DEFAULT_MODEL = "claude-opus-5"

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


class AnthropicProvider:
    """Claude, via the Messages API."""

    name = "anthropic"

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        self._key = (api_key if api_key is not None else os.getenv(KEY_ENV_VAR) or "").strip()
        self._model = (model or os.getenv(MODEL_ENV_VAR) or DEFAULT_MODEL).strip()
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
        self._client = AsyncAnthropic(api_key=self._key, timeout=REQUEST_TIMEOUT_SECONDS)
        return self._client

    async def complete(
        self, *, system: str, messages: list[dict], tools: list[dict],
    ) -> LlmReply:
        client = self._ensure_client()
        try:
            response = await client.messages.create(
                model=self._model,
                max_tokens=MAX_OUTPUT_TOKENS,
                system=system,
                messages=messages,
                tools=tools or [],
            )
        except Exception as exc:
            # The message may carry request detail; the type alone is enough to
            # act on and cannot leak a key or a prompt into a log.
            self._last_error = type(exc).__name__
            log.warning("Edge AI request failed: %s", type(exc).__name__)
            raise ProviderUnavailable("the assistant is temporarily unreachable") from exc

        self._last_error = ""
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
        return LlmReply(
            text="\n".join(t for t in text_parts if t).strip(),
            tool_calls=calls,
            stop_reason=getattr(response, "stop_reason", "") or "",
            input_tokens=getattr(usage, "input_tokens", 0) or 0,
            output_tokens=getattr(usage, "output_tokens", 0) or 0,
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
