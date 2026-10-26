"""Local stand-ins for chat APIs. Tests point real clients at these servers over HTTP.

No key, no network and no cost. `stub_api` speaks the Anthropic Messages format,
`stub_openai` speaks the OpenAI chat format.
"""

import json
import threading
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Any, cast

# Takes the messages sent so far, returns (content blocks, stop_reason) for Anthropic.
Decide = Callable[[list[dict[str, Any]]], tuple[list[dict[str, Any]], str]]
# Takes the chat messages sent so far, returns (assistant message, finish_reason) for OpenAI.
DecideChat = Callable[[list[dict[str, Any]]], tuple[dict[str, Any], str]]


class _Server(HTTPServer):
    respond: Callable[[dict[str, Any]], dict[str, Any]]


class _Handler(BaseHTTPRequestHandler):
    def do_POST(self) -> None:
        body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        data = json.dumps(cast(_Server, self.server).respond(body)).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, format: str, *args: Any) -> None:
        return  # keep test output clean


@contextmanager
def _serve(respond: Callable[[dict[str, Any]], dict[str, Any]]) -> Iterator[str]:
    """Serve on a free local port for the duration of the block. Yields the base URL."""
    server = _Server(("127.0.0.1", 0), _Handler)
    server.respond = respond
    threading.Thread(target=server.serve_forever, daemon=True).start()
    try:
        yield f"http://127.0.0.1:{server.server_port}"
    finally:
        server.shutdown()
        server.server_close()


def stub_api(decide: Decide) -> Any:
    """Anthropic Messages format. Use with `with stub_api(...) as url`."""

    def respond(body: dict[str, Any]) -> dict[str, Any]:
        content, stop_reason = decide(body["messages"])
        return {
            "id": "msg_stub",
            "type": "message",
            "role": "assistant",
            "model": body["model"],
            "content": content,
            "stop_reason": stop_reason,
            "stop_sequence": None,
            "usage": {"input_tokens": 1, "output_tokens": 1},
        }

    return _serve(respond)


def stub_openai(decide: DecideChat) -> Any:
    """OpenAI chat format. Use with `with stub_openai(...) as url`; url is the /v1 base."""

    def respond(body: dict[str, Any]) -> dict[str, Any]:
        message, finish_reason = decide(body["messages"])
        return {"choices": [{"message": message, "finish_reason": finish_reason}]}

    return _serve(respond)


def asks_for(name: str, args: dict[str, Any]) -> Decide:
    """Anthropic-style model: calls `name` once, then answers with the tool result it got."""

    def decide(messages: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], str]:
        last = messages[-1]["content"]
        if isinstance(last, list) and last[0].get("type") == "tool_result":
            return [{"type": "text", "text": f"result: {last[0]['content']}"}], "end_turn"
        block = {"type": "tool_use", "id": "toolu_stub", "name": name, "input": args}
        return [block], "tool_use"

    return decide


def openai_asks_for(name: str, args: dict[str, Any]) -> DecideChat:
    """OpenAI-style model: calls `name` once, then answers with the tool result it got."""

    def decide(messages: list[dict[str, Any]]) -> tuple[dict[str, Any], str]:
        last = messages[-1]
        if last["role"] == "tool":
            return {"role": "assistant", "content": f"result: {last['content']}"}, "stop"
        call = {
            "id": "call_stub",
            "type": "function",
            "function": {"name": name, "arguments": json.dumps(args)},
        }
        return {"role": "assistant", "content": None, "tool_calls": [call]}, "tool_calls"

    return decide
