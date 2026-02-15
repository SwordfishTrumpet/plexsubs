"""Retry utilities and decorators."""

import asyncio
import functools
import time
from typing import Callable, Optional, TypeVar

from plexsubs.utils.constants import (
    DEFAULT_BASE_RETRY_DELAY,
    DEFAULT_MAX_RETRIES,
)

T = TypeVar("T")


def retry_with_backoff(
    max_retries: int = DEFAULT_MAX_RETRIES,
    base_delay: float = DEFAULT_BASE_RETRY_DELAY,
    exceptions: tuple[type[Exception], ...] = (Exception,),
    on_retry: Optional[Callable[[int, float, Exception], None]] = None,
) -> Callable:
    """Decorator for retrying functions with exponential backoff.

    Works with both synchronous and asynchronous functions.

    Args:
        max_retries: Maximum number of retry attempts
        base_delay: Initial delay between retries (doubles each attempt)
        exceptions: Tuple of exception types to catch and retry
        on_retry: Optional callback function called on each retry

    Returns:
        Decorated function
    """

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs) -> T:
            for attempt in range(max_retries):
                try:
                    return await func(*args, **kwargs)
                except exceptions as e:
                    if attempt < max_retries - 1:
                        delay = base_delay * (2**attempt)
                        if on_retry:
                            on_retry(attempt, delay, e)
                        await asyncio.sleep(delay)
                    else:
                        raise

            # Should not reach here
            raise RuntimeError("Retry loop exited unexpectedly")

        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs) -> T:
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    if attempt < max_retries - 1:
                        delay = base_delay * (2**attempt)
                        if on_retry:
                            on_retry(attempt, delay, e)
                        time.sleep(delay)
                    else:
                        raise

            # Should not reach here
            raise RuntimeError("Retry loop exited unexpectedly")

        # Return async wrapper if function is async, sync wrapper otherwise
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper

    return decorator


# Backward compatibility alias
retry_async_with_backoff = retry_with_backoff
