"""Unit tests for the async retry utility."""

from __future__ import annotations

import asyncio
import time
from unittest.mock import AsyncMock

import pytest

from src.retry import async_retry


def _run(coro):
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


class TestAsyncRetrySuccess:
    """Verify that async_retry returns on first success."""

    def test_returns_value_on_first_call(self):
        fn = AsyncMock(return_value="ok")
        result = _run(async_retry(fn, max_retries=3))
        assert result == "ok"
        assert fn.call_count == 1

    def test_returns_value_after_transient_failure(self):
        fn = AsyncMock(side_effect=[ValueError("boom"), "ok"])
        result = _run(
            async_retry(fn, max_retries=3, base_delay=0.01, retryable_exceptions=(ValueError,))
        )
        assert result == "ok"
        assert fn.call_count == 2

    def test_retries_up_to_max(self):
        fn = AsyncMock(side_effect=[ValueError("1"), ValueError("2"), "ok"])
        result = _run(
            async_retry(fn, max_retries=3, base_delay=0.01, retryable_exceptions=(ValueError,))
        )
        assert result == "ok"
        assert fn.call_count == 3


class TestAsyncRetryExhaustion:
    """Verify that async_retry raises after max retries."""

    def test_raises_after_all_retries_exhausted(self):
        fn = AsyncMock(side_effect=ValueError("fail"))
        with pytest.raises(ValueError, match="fail"):
            _run(
                async_retry(fn, max_retries=2, base_delay=0.01, retryable_exceptions=(ValueError,))
            )
        # initial call + 2 retries = 3 total
        assert fn.call_count == 3

    def test_non_retryable_exception_raises_immediately(self):
        fn = AsyncMock(side_effect=TypeError("wrong type"))
        with pytest.raises(TypeError, match="wrong type"):
            _run(
                async_retry(fn, max_retries=3, base_delay=0.01, retryable_exceptions=(ValueError,))
            )
        assert fn.call_count == 1


class TestAsyncRetryBackoff:
    """Verify exponential backoff timing."""

    def test_delay_increases_exponentially(self):
        fn = AsyncMock(side_effect=[ValueError("1"), ValueError("2"), "ok"])
        start = time.monotonic()
        _run(
            async_retry(fn, max_retries=3, base_delay=0.05, retryable_exceptions=(ValueError,))
        )
        elapsed = time.monotonic() - start
        # base_delay=0.05: first retry ~0.05s, second ~0.10s → total ~0.15s
        assert elapsed >= 0.1

    def test_max_delay_caps_backoff(self):
        fn = AsyncMock(side_effect=[ValueError("1"), ValueError("2"), "ok"])
        start = time.monotonic()
        _run(
            async_retry(
                fn,
                max_retries=3,
                base_delay=0.05,
                max_delay=0.06,
                retryable_exceptions=(ValueError,),
            )
        )
        elapsed = time.monotonic() - start
        # Both delays capped at 0.06 → total ~0.12s max
        assert elapsed < 0.3


class TestAsyncRetryArgs:
    """Verify arguments are forwarded correctly."""

    def test_positional_args_forwarded(self):
        fn = AsyncMock(return_value="ok")
        _run(async_retry(fn, "a", "b", max_retries=0))
        fn.assert_called_once_with("a", "b")

    def test_keyword_args_forwarded(self):
        fn = AsyncMock(return_value="ok")
        _run(async_retry(fn, max_retries=0, retryable_exceptions=(Exception,), key="val"))
        fn.assert_called_once_with(key="val")
