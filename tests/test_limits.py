import httpx
import pytest

from agent_runtime.harness.limits import retry


def _status_error(code: int) -> httpx.HTTPStatusError:
    request = httpx.Request("POST", "http://x")
    response = httpx.Response(code, request=request)
    return httpx.HTTPStatusError("boom", request=request, response=response)


def test_a_401_is_not_retried() -> None:
    calls: list[int] = []

    def fn() -> str:
        calls.append(1)
        raise _status_error(401)

    with pytest.raises(httpx.HTTPStatusError):
        retry(fn, base_delay_s=0)
    assert len(calls) == 1


def test_rate_limits_and_server_errors_are_retried_until_they_clear() -> None:
    errors = [_status_error(503), _status_error(429)]

    def fn() -> str:
        if errors:
            raise errors.pop(0)
        return "ok"

    assert retry(fn, base_delay_s=0) == "ok"
