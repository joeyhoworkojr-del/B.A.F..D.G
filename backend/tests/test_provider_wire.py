"""
What the Anthropic provider actually puts on the wire.

Every other Edge AI test swaps in a fake provider, which is right for testing
the assistant but leaves the request itself unexercised: a malformed body, a
dropped header or a tool schema the API rejects would pass the whole suite and
fail on every request in production. These tests run the real SDK against a
local server and read back what it sent.

Nothing here reaches the internet, and the key is a placeholder.
"""
from __future__ import annotations

import asyncio
import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

import pytest

from src.ai import edge_ai
from src.ai import provider as P

OK_BODY = {
    "id": "msg_1", "type": "message", "role": "assistant", "model": "claude-haiku-4-5",
    "content": [{"type": "text", "text": "hello"}],
    "stop_reason": "end_turn", "stop_sequence": None,
    "usage": {"input_tokens": 12, "output_tokens": 3,
              "cache_creation_input_tokens": 40, "cache_read_input_tokens": 5},
}


class _Recorder:
    """A one-request Anthropic stand-in that keeps what it was sent."""

    def __init__(self, status: int = 200, body: dict | None = None):
        self.status = status
        self.body = OK_BODY if body is None else body
        self.seen: dict = {}
        outer = self

        class Handler(BaseHTTPRequestHandler):
            def do_POST(self):
                length = int(self.headers.get("content-length", 0))
                outer.seen = {
                    "path": self.path,
                    "body": json.loads(self.rfile.read(length) or b"{}"),
                    "headers": dict(self.headers),
                }
                payload = json.dumps(outer.body).encode()
                self.send_response(outer.status)
                self.send_header("content-type", "application/json")
                self.send_header("content-length", str(len(payload)))
                self.end_headers()
                self.wfile.write(payload)

            def log_message(self, *_a):  # keep pytest output clean
                pass

        self._server = HTTPServer(("127.0.0.1", 0), Handler)
        self.url = f"http://127.0.0.1:{self._server.server_port}"

    def __enter__(self):
        threading.Thread(target=self._server.serve_forever, daemon=True).start()
        return self

    def __exit__(self, *_exc):
        self._server.shutdown()
        self._server.server_close()


@pytest.fixture
def no_proxy(monkeypatch):
    # httpx honours the ambient proxy variables, which would send a request for
    # localhost out through a proxy that cannot answer it.
    for var in ("HTTP_PROXY", "HTTPS_PROXY", "http_proxy", "https_proxy", "ALL_PROXY"):
        monkeypatch.delenv(var, raising=False)


def _provider_pointed_at(url: str) -> P.AnthropicProvider:
    from anthropic import AsyncAnthropic
    prov = P.AnthropicProvider(api_key="sk-ant-placeholder-000", model="claude-haiku-4-5")
    prov._client = AsyncAnthropic(
        api_key="sk-ant-placeholder-000", base_url=url, timeout=10.0, max_retries=0,
    )
    return prov


def _ask(prov: P.AnthropicProvider, tools: list[dict]):
    return asyncio.run(prov.complete(
        system="You are Edge.",
        messages=[{"role": "user", "content": "hi"}],
        tools=tools,
    ))


def test_the_request_reaches_the_messages_endpoint_in_the_documented_shape(no_proxy):
    with _Recorder() as rec:
        _ask(_provider_pointed_at(rec.url), edge_ai.TOOLS)

    assert rec.seen["path"] == "/v1/messages"
    assert rec.seen["headers"].get("anthropic-version")
    body = rec.seen["body"]
    assert body["model"] == "claude-haiku-4-5"
    assert body["max_tokens"] == P.MAX_OUTPUT_TOKENS
    assert body["messages"] == [{"role": "user", "content": "hi"}]


def test_the_cached_prefix_is_marked_on_the_system_block(no_proxy):
    # Caching is the difference between Edge AI costing pennies and costing
    # real money, and it is invisible from anywhere except the request body.
    with _Recorder() as rec:
        _ask(_provider_pointed_at(rec.url), edge_ai.TOOLS)

    system = rec.seen["body"]["system"]
    assert isinstance(system, list) and len(system) == 1
    assert system[0]["type"] == "text"
    assert system[0]["cache_control"] == {"type": "ephemeral"}


def test_every_tool_survives_serialisation_with_the_keys_the_api_requires(no_proxy):
    with _Recorder() as rec:
        _ask(_provider_pointed_at(rec.url), edge_ai.TOOLS)

    sent = rec.seen["body"]["tools"]
    assert len(sent) == len(edge_ai.TOOLS)
    assert {t["name"] for t in sent} == edge_ai.TOOL_NAMES
    for tool in sent:
        assert set(tool) >= {"name", "description", "input_schema"}
        assert tool["input_schema"]["type"] == "object"


def test_cache_reads_and_writes_are_counted_as_input_not_lost(no_proxy):
    # They are billed, so a budget that ignores them under-reports the spend.
    with _Recorder() as rec:
        reply = _ask(_provider_pointed_at(rec.url), edge_ai.TOOLS)

    assert reply.text == "hello"
    assert reply.input_tokens == 12 + 40 + 5
    assert reply.cached_tokens == 5
    assert reply.output_tokens == 3


def test_a_tool_call_comes_back_as_a_tool_call(no_proxy):
    body = dict(OK_BODY, stop_reason="tool_use", content=[
        {"type": "text", "text": "Looking that up."},
        {"type": "tool_use", "id": "tu_1", "name": "get_todays_games",
         "input": {"league": "nfl"}},
    ])
    with _Recorder(body=body) as rec:
        reply = _ask(_provider_pointed_at(rec.url), edge_ai.TOOLS)

    assert reply.wants_tools
    assert [c.name for c in reply.tool_calls] == ["get_todays_games"]
    assert reply.tool_calls[0].arguments == {"league": "nfl"}


def test_a_rejected_model_is_reported_as_a_model_problem_not_a_blackout(no_proxy):
    body = {"type": "error", "error": {"type": "not_found_error",
                                       "message": "model: claude-haiku-4-5"}}
    with _Recorder(status=404, body=body) as rec:
        prov = _provider_pointed_at(rec.url)
        with pytest.raises(P.ProviderUnavailable) as exc:
            _ask(prov, edge_ai.TOOLS)

    assert "model this account cannot use" in str(exc.value)
    # And staff get the detail the user does not need.
    assert "404" in prov.status()["last_error"]


def test_a_rejected_key_says_so_rather_than_blaming_the_network(no_proxy):
    body = {"type": "error", "error": {"type": "authentication_error",
                                       "message": "invalid x-api-key"}}
    with _Recorder(status=401, body=body) as rec:
        with pytest.raises(P.ProviderUnavailable) as exc:
            _ask(_provider_pointed_at(rec.url), edge_ai.TOOLS)

    assert "key was rejected" in str(exc.value)


def test_an_error_carrying_a_key_is_scrubbed_before_it_is_stored(no_proxy):
    leaked = "sk-ant-api03-THISLOOKSLIKEAREALKEY"
    body = {"type": "error", "error": {"type": "invalid_request_error",
                                       "message": f"bad header {leaked}"}}
    with _Recorder(status=400, body=body) as rec:
        prov = _provider_pointed_at(rec.url)
        with pytest.raises(P.ProviderUnavailable):
            _ask(prov, edge_ai.TOOLS)

    stored = prov.status()["last_error"]
    assert leaked not in stored
    assert "sk-***" in stored


def test_a_workspace_id_travels_on_every_request_when_configured(no_proxy):
    # An organisation-level key is not tied to a workspace, and the API will
    # not guess which one to bill. This is what makes such a key usable
    # without anyone reissuing it.
    with _Recorder() as rec:
        from anthropic import AsyncAnthropic
        prov = P.AnthropicProvider(
            api_key="sk-ant-placeholder-000", model="claude-haiku-4-5",
            workspace_id="wrkspc_123",
        )
        prov._client = AsyncAnthropic(
            api_key="sk-ant-placeholder-000", base_url=rec.url,
            timeout=10.0, max_retries=0,
            default_headers={P.WORKSPACE_HEADER: "wrkspc_123"},
        )
        _ask(prov, edge_ai.TOOLS)

    assert rec.seen["headers"].get(P.WORKSPACE_HEADER) == "wrkspc_123"


def test_no_workspace_header_is_sent_when_none_is_configured(no_proxy):
    # A workspace-scoped key already carries its workspace; naming a different
    # one on such a key is an error, not an override.
    with _Recorder() as rec:
        _ask(_provider_pointed_at(rec.url), edge_ai.TOOLS)

    assert P.WORKSPACE_HEADER not in {k.lower() for k in rec.seen["headers"]}


def test_the_unscoped_key_error_names_the_setting_that_fixes_it(no_proxy):
    # The exact body the live deployment came back with. It was reaching the
    # user as "temporarily unreachable", which named nothing at all.
    body = {"type": "error", "error": {
        "type": "invalid_request_error",
        "message": ("This API key is not scoped to a workspace, so this request must "
                    "include the anthropic-workspace-id header with the ID of the "
                    "workspace to use. Add the header, or use an API key that is "
                    "scoped to a workspace.")}}
    with _Recorder(status=400, body=body) as rec:
        with pytest.raises(P.ProviderUnavailable) as exc:
            _ask(_provider_pointed_at(rec.url), edge_ai.TOOLS)

    message = str(exc.value)
    assert P.WORKSPACE_ENV_VAR in message
    # And it must not be mistaken for the model being wrong, which would send
    # whoever reads it to change a setting that is already correct.
    assert "model this account cannot use" not in message


def test_the_status_report_says_whether_a_workspace_is_set_but_never_which(no_proxy):
    prov = P.AnthropicProvider(api_key="sk-ant-placeholder-000",
                               workspace_id="wrkspc_secret")
    report = prov.status()
    assert report["workspace_scoped"] is True
    assert "wrkspc_secret" not in repr(report)
