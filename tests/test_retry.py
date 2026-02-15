"""Tests for retry decorator."""

import asyncio
import time

import pytest

from plexsubs.utils.retry import retry_with_backoff


class TestRetryWithBackoffSync:
    """Tests for synchronous retry decorator."""

    def test_success_no_retry(self):
        """Test successful function doesn't retry."""
        call_count = 0

        @retry_with_backoff(max_retries=3, base_delay=0.01)
        def success_func():
            nonlocal call_count
            call_count += 1
            return "success"

        result = success_func()
        assert result == "success"
        assert call_count == 1

    def test_retry_then_success(self):
        """Test retry on failure then success."""
        call_count = 0

        @retry_with_backoff(max_retries=3, base_delay=0.01)
        def fail_then_succeed():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ValueError("Temporary failure")
            return "success"

        result = fail_then_succeed()
        assert result == "success"
        assert call_count == 3

    def test_max_retries_exceeded(self):
        """Test exception raised after max retries."""
        call_count = 0

        @retry_with_backoff(max_retries=3, base_delay=0.01)
        def always_fail():
            nonlocal call_count
            call_count += 1
            raise ValueError("Persistent failure")

        with pytest.raises(ValueError, match="Persistent failure"):
            always_fail()

        assert call_count == 3

    def test_specific_exception_type(self):
        """Test only specified exceptions trigger retry."""
        call_count = 0

        @retry_with_backoff(max_retries=3, base_delay=0.01, exceptions=(ValueError,))
        def mixed_failures():
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise TypeError("Not retried")  # Different exception
            raise ValueError("Retried")

        with pytest.raises(TypeError, match="Not retried"):
            mixed_failures()

        assert call_count == 1  # No retry for TypeError

    def test_on_retry_callback(self):
        """Test on_retry callback is called."""
        callback_calls = []

        def on_retry(attempt, delay, exception):
            callback_calls.append((attempt, delay, str(exception)))

        @retry_with_backoff(max_retries=3, base_delay=0.01, on_retry=on_retry)
        def fail_twice():
            if len(callback_calls) < 2:
                raise ValueError("Error")
            return "success"

        fail_twice()

        assert len(callback_calls) == 2
        assert callback_calls[0][0] == 0
        assert callback_calls[0][1] == 0.01  # base_delay * 2^0
        assert callback_calls[1][0] == 1
        assert callback_calls[1][1] == 0.02  # base_delay * 2^1

    def test_exponential_backoff_timing(self):
        """Test exponential backoff delays."""
        delays = []

        def on_retry(attempt, delay, exception):
            delays.append(delay)

        @retry_with_backoff(max_retries=4, base_delay=0.01, on_retry=on_retry)
        def always_fail():
            raise ValueError("Fail")

        with pytest.raises(ValueError):
            always_fail()

        # Exponential backoff: 0.01, 0.02, 0.04
        assert delays == [0.01, 0.02, 0.04]

    def test_preserves_function_metadata(self):
        """Test decorator preserves function name and docstring."""

        @retry_with_backoff(max_retries=2, base_delay=0.01)
        def my_function():
            """My docstring."""
            return "result"

        assert my_function.__name__ == "my_function"
        assert my_function.__doc__ == "My docstring."

    def test_function_with_arguments(self):
        """Test retry with function arguments."""
        call_args = []

        @retry_with_backoff(max_retries=2, base_delay=0.01)
        def func_with_args(a, b, c=None, **kwargs):
            call_args.append((a, b, c, kwargs))
            if len(call_args) < 2:
                raise ValueError("Retry")
            return a + b

        result = func_with_args(1, 2, c=3, extra="value")

        assert result == 3
        assert len(call_args) == 2
        assert call_args[0] == (1, 2, 3, {"extra": "value"})


class TestRetryWithBackoffAsync:
    """Tests for asynchronous retry decorator."""

    @pytest.mark.asyncio
    async def test_async_success_no_retry(self):
        """Test successful async function doesn't retry."""
        call_count = 0

        @retry_with_backoff(max_retries=3, base_delay=0.01)
        async def async_success():
            nonlocal call_count
            call_count += 1
            await asyncio.sleep(0.001)
            return "async success"

        result = await async_success()
        assert result == "async success"
        assert call_count == 1

    @pytest.mark.asyncio
    async def test_async_retry_then_success(self):
        """Test async retry on failure then success."""
        call_count = 0

        @retry_with_backoff(max_retries=3, base_delay=0.01)
        async def async_fail_then_succeed():
            nonlocal call_count
            call_count += 1
            await asyncio.sleep(0.001)
            if call_count < 3:
                raise ValueError("Temporary failure")
            return "async success"

        result = await async_fail_then_succeed()
        assert result == "async success"
        assert call_count == 3

    @pytest.mark.asyncio
    async def test_async_max_retries_exceeded(self):
        """Test async exception raised after max retries."""
        call_count = 0

        @retry_with_backoff(max_retries=3, base_delay=0.01)
        async def async_always_fail():
            nonlocal call_count
            call_count += 1
            await asyncio.sleep(0.001)
            raise ConnectionError("Network error")

        with pytest.raises(ConnectionError, match="Network error"):
            await async_always_fail()

        assert call_count == 3

    @pytest.mark.asyncio
    async def test_async_specific_exception(self):
        """Test async only specified exceptions trigger retry."""
        call_count = 0

        @retry_with_backoff(max_retries=3, base_delay=0.01, exceptions=(ConnectionError,))
        async def async_mixed_failures():
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise ValueError("Not retried")
            raise ConnectionError("Retried")

        with pytest.raises(ValueError, match="Not retried"):
            await async_mixed_failures()

        assert call_count == 1

    @pytest.mark.asyncio
    async def test_async_preserves_metadata(self):
        """Test async decorator preserves function metadata."""

        @retry_with_backoff(max_retries=2, base_delay=0.01)
        async def async_function():
            """Async docstring."""
            return "result"

        assert async_function.__name__ == "async_function"
        assert async_function.__doc__ == "Async docstring."


class TestRetryEdgeCases:
    """Tests for edge cases."""

    def test_max_retries_zero(self):
        """Test with max_retries=0 - should not call function."""
        # Edge case: With max_retries=0, the for loop range(0) never executes
        # This means the function body never runs!
        call_count = 0

        @retry_with_backoff(max_retries=0, base_delay=0.01)
        def never_called():
            nonlocal call_count
            call_count += 1
            return "result"

        # This raises RuntimeError because the loop exits unexpectedly
        with pytest.raises(RuntimeError, match="Retry loop exited unexpectedly"):
            never_called()

        assert call_count == 0  # Function was never actually called!

    def test_max_retries_one(self):
        """Test with max_retries=1 - no retries, just one attempt."""
        call_count = 0

        @retry_with_backoff(max_retries=1, base_delay=0.01)
        def single_attempt():
            nonlocal call_count
            call_count += 1
            raise ValueError("Fail")

        with pytest.raises(ValueError):
            single_attempt()

        assert call_count == 1  # Only one attempt, no retries

    def test_base_delay_zero(self):
        """Test with zero base delay - retries immediately."""
        call_count = 0
        start_time = time.time()

        @retry_with_backoff(max_retries=3, base_delay=0)
        def fast_retry():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ValueError("Retry")
            return "done"

        result = fast_retry()
        elapsed = time.time() - start_time

        assert result == "done"
        assert call_count == 3
        assert elapsed < 0.1  # Should be very fast with no delay

    def test_exception_subclass_matching(self):
        """Test that exception subclasses are caught."""
        call_count = 0

        @retry_with_backoff(max_retries=3, base_delay=0.01, exceptions=(Exception,))
        def subclass_exception():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ValueError("Subclass of Exception")
            return "success"

        result = subclass_exception()
        assert result == "success"
        assert call_count == 3

    def test_tuple_of_exceptions(self):
        """Test multiple exception types in tuple."""
        call_count = 0
        exceptions_to_raise = [ValueError, TypeError, KeyError]

        @retry_with_backoff(
            max_retries=4, base_delay=0.01, exceptions=(ValueError, TypeError, KeyError)
        )
        def various_exceptions():
            nonlocal call_count
            if call_count < 3:
                exc = exceptions_to_raise[call_count]
                call_count += 1
                raise exc("Error")
            call_count += 1
            return "success"

        result = various_exceptions()
        assert result == "success"
        assert call_count == 4
