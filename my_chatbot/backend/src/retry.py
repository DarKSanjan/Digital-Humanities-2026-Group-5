"""Async retry utility with exponential backoff.

Provides a generic async retry wrapper for transient API failures.
Used by the streaming pipeline and app controller to retry STT, LLM,
and TTS calls.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Awaitable, Callable, TypeVar

logger = logging.getLogger(__name__)

T = TypeVar("T")

# Defaults
DEFAULT_MAX_RETRIES = 3
DEFAULT_BASE_DELAY = 1.0
DEFAULT_MAX_DELAY = 10.0


async def async_retry(
    fn: Callable[..., Awaitable[T]],
    *args,
    max_retries: int = DEFAULT_MAX_RETRIES,
    base_delay: float = DEFAULT_BASE_DELAY,
    max_delay: float = DEFAULT_MAX_DELAY,
    retryable_exceptions: tuple[type[Exception], ...] = (Exception,),
    **kwargs,
) -> T:
    """Call *fn* with retry and exponential backoff.

    Parameters
    ----------
    fn:
        An async callable to invoke.
    *args:
        Positional arguments forwarded to *fn*.
    max_retries:
        Maximum number of retry attempts (not counting the initial call).
    base_delay:
        Initial delay in seconds before the first retry.
    max_delay:
        Cap on the backoff delay.
    retryable_exceptions:
        Tuple of exception types that should trigger a retry.
    **kwargs:
        Keyword arguments forwarded to *fn*.

    Returns
    -------
    T
        The return value of *fn*.

    Raises
    ------
    Exception
        The last exception raised by *fn* if all retries are exhausted.
    """
    last_exc: Exception | None = None

    for attempt in range(max_retries + 1):
        try:
            return await fn(*args, **kwargs)
        except retryable_exceptions as exc:
            last_exc = exc
            if attempt == max_retries:
                logger.error(
                    "All %d retries exhausted for %s: %s",
                    max_retries,
                    fn.__name__ if hasattr(fn, "__name__") else str(fn),
                    exc,
                )
                raise
            delay = min(base_delay * (2 ** attempt), max_delay)
            logger.warning(
                "Attempt %d/%d for %s failed (%s), retrying in %.1fs",
                attempt + 1,
                max_retries + 1,
                fn.__name__ if hasattr(fn, "__name__") else str(fn),
                exc,
                delay,
            )
            await asyncio.sleep(delay)

    # Should never reach here, but satisfy type checker
    assert last_exc is not None
    raise last_exc
