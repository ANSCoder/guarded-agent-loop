"""Adapter for any OpenAI-style chat API: Ollama, Hugging Face, Groq, OpenRouter, and similar.

The loop speaks Anthropic content blocks. This module converts them to chat messages and turns
the reply back into blocks. It covers text and tool calls only.
"""

import json
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

import httpx

FINISH = {"tool_calls": "tool_use", "length": "max_tokens"}


class ModelReplyError(Exception):
    """The server answered 200 but the body is not a chat completion we can read."""


@dataclass
class Block:
    """One reply block, shaped like an Anthropic content block."""

    type: str
    text: str = ""
    id: str = ""
    name: str = ""
    input: dict[str, Any] = field(default_factory=dict)


@dataclass
class Reply:
    """What `create` returns: content blocks and a stop reason in the loop's terms."""

    content: list[Block]
    stop_reason: str


def _chat_messages(system: str, messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Convert loop messages (content blocks) to chat messages (role and content)."""
    out: list[dict[str, Any]] = [{"role": "system", "content": system}]
    for msg in messages:
        content = msg["content"]
        if isinstance(content, str):
            out.append({"role": msg["role"], "content": content})
        elif msg["role"] == "assistant":
            text = "".join(b["text"] for b in content if b["type"] == "text")
            calls = [
                {
                    "id": b["id"],
                    "type": "function",
                    "function": {"name": b["name"], "arguments": json.dumps(b["input"])},
                }
                for b in content
                if b["type"] == "tool_use"
            ]
            out.append(
                {"role": "assistant", "content": text, **({"tool_calls": calls} if calls else {})}
            )
        else:  # a user turn carrying tool results: one chat message per result
            for b in content:
                out.append(
                    {"role": "tool", "tool_call_id": b["tool_use_id"], "content": b["content"]}
                )
    return out


def parse_reply(message: dict[str, Any], finish_reason: str) -> Reply:
    """Turn one chat reply into content blocks and a loop stop reason."""
    blocks: list[Block] = []
    if message.get("content"):
        blocks.append(Block("text", text=message["content"]))
    calls = message.get("tool_calls") or []
    for i, call in enumerate(calls):
        arguments = call["function"]["arguments"]
        # Cut-off JSON from a small model becomes {}: the tool fails, and the model can retry.
        try:
            args = json.loads(arguments) if isinstance(arguments, str) else arguments
        except json.JSONDecodeError:
            args = {}
        blocks.append(
            Block(
                "tool_use",
                id=call.get("id") or f"call_{i}",
                name=call["function"]["name"],
                input=args,
            )
        )
    stop = "tool_use" if calls else FINISH.get(finish_reason, "end_turn")
    return Reply(blocks, stop)


def make_create(
    base_url: str, api_key: str | None = None, reasoning_effort: str = ""
) -> Callable[..., Reply]:
    """Return a `create` for the runtime that calls `base_url`/chat/completions.

    reasoning_effort is sent only when set. "none" makes Ollama's thinking models skip their
    reasoning, which is several times faster. Not every provider accepts it, so it is off.
    """

    def create(
        *,
        model: str,
        max_tokens: int,
        system: str,
        tools: list[dict[str, Any]],
        messages: list[dict[str, Any]],
        timeout: float,
    ) -> Reply:
        body: dict[str, Any] = {
            "model": model,
            "max_tokens": max_tokens,
            "messages": _chat_messages(system, messages),
            "tools": [
                {
                    "type": "function",
                    "function": {
                        "name": t["name"],
                        "description": t["description"],
                        "parameters": t["input_schema"],
                    },
                }
                for t in tools
            ],
        }
        if reasoning_effort:
            body["reasoning_effort"] = reasoning_effort
        headers = {"Authorization": f"Bearer {api_key}"} if api_key else {}
        response = httpx.post(
            f"{base_url.rstrip('/')}/chat/completions", json=body, headers=headers, timeout=timeout
        )
        response.raise_for_status()
        try:
            choice = response.json()["choices"][0]
            return parse_reply(choice["message"], choice["finish_reason"])
        except (ValueError, KeyError, IndexError, TypeError) as exc:
            raise ModelReplyError(f"unexpected reply from {base_url}: {exc!r}") from exc

    return create
