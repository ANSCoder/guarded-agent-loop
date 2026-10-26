import httpx
import pytest

from agent_runtime.openai_compat import ModelReplyError, make_create, parse_reply


def test_tool_call_reply_becomes_tool_use_block() -> None:
    message = {
        "content": None,
        "tool_calls": [
            {"id": "c1", "function": {"name": "calculator", "arguments": '{"expression": "2+2"}'}}
        ],
    }
    reply = parse_reply(message, "tool_calls")
    assert reply.stop_reason == "tool_use"
    assert (reply.content[0].name, reply.content[0].input) == ("calculator", {"expression": "2+2"})


def test_broken_tool_arguments_become_empty_input() -> None:
    message = {
        "content": None,
        "tool_calls": [
            {"id": "c1", "function": {"name": "calculator", "arguments": '{"expression": "2+2"'}}
        ],
    }
    reply = parse_reply(message, "tool_calls")
    assert (reply.stop_reason, reply.content[0].input) == ("tool_use", {})


def test_a_reply_without_choices_is_a_clear_error(monkeypatch: pytest.MonkeyPatch) -> None:
    request = httpx.Request("POST", "http://x/chat/completions")
    busy = httpx.Response(200, json={"error": "busy"}, request=request)
    monkeypatch.setattr(httpx, "post", lambda *args, **kwargs: busy)
    create = make_create("http://x")
    with pytest.raises(ModelReplyError, match="unexpected reply"):
        create(model="m", max_tokens=1, system="s", tools=[], messages=[], timeout=1.0)


def test_reasoning_effort_is_sent_only_when_set(monkeypatch: pytest.MonkeyPatch) -> None:
    sent: list[dict[str, object]] = []
    request = httpx.Request("POST", "http://x/chat/completions")
    ok = httpx.Response(
        200,
        json={"choices": [{"message": {"content": "hi"}, "finish_reason": "stop"}]},
        request=request,
    )

    def fake_post(url: str, *, json: dict[str, object], **kwargs: object) -> httpx.Response:
        sent.append(json)
        return ok

    monkeypatch.setattr(httpx, "post", fake_post)
    call = {
        "model": "m",
        "max_tokens": 1,
        "system": "s",
        "tools": [],
        "messages": [],
        "timeout": 1.0,
    }
    make_create("http://x")(**call)
    make_create("http://x", reasoning_effort="none")(**call)
    assert "reasoning_effort" not in sent[0]
    assert sent[1]["reasoning_effort"] == "none"


def test_length_finish_maps_to_max_tokens() -> None:
    reply = parse_reply({"content": "half"}, "length")
    assert (reply.stop_reason, reply.content[0].text) == ("max_tokens", "half")
