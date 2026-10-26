"""Timeouts, output caps and retries for tool and model calls."""

import time
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from typing import Any, TypeVar

import anthropic
import httpx

T = TypeVar("T")

RETRYABLE = (
    anthropic.APIConnectionError,
    anthropic.RateLimitError,
    anthropic.InternalServerError,
    httpx.TransportError,
    httpx.HTTPStatusError,
)


def call_with_timeout(
    fn: Callable[[dict[str, Any]], str], args: dict[str, Any], timeout_s: float
) -> str:
    # shortcut: a timed-out tool keeps running in its thread, upgrade to a subprocess for hangs
    """Run a tool in a thread and stop waiting after timeout_s. The thread is not killed."""
    pool = ThreadPoolExecutor(max_workers=1)
    try:
        return pool.submit(fn, args).result(timeout=timeout_s)
    finally:
        pool.shutdown(wait=False, cancel_futures=True)


def cap_output(text: str, cap: int) -> str:
    """Cut text to cap characters and say how many were dropped."""
    if len(text) <= cap:
        return text
    return f"{text[:cap]}\n[truncated {len(text) - cap} chars]"


def _worth_retrying(exc: Exception) -> bool:
    # A 401 or 400 will fail the same way again. Only 429 and 5xx can clear up.
    if isinstance(exc, httpx.HTTPStatusError):
        code = exc.response.status_code
        return code == 429 or code >= 500
    return True


def retry(fn: Callable[[], T], attempts: int = 3, base_delay_s: float = 1.0) -> T:
    """Call fn again after rate limits, connection errors or server errors, with backoff."""
    for attempt in range(attempts):
        try:
            return fn()
        except RETRYABLE as exc:
            if attempt == attempts - 1 or not _worth_retrying(exc):
                raise
            time.sleep(base_delay_s * 2**attempt)
    raise AssertionError("unreachable")
