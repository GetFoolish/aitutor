"""
Test suite for ThreadPoolExecutor timeout fix.

Validates that timeout fixes actually work with wall-clock timing proof.
"""

import time
import pytest
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeoutError


class TestExecutorTimeout:
    """Test that executor timeouts are actually fast."""

    def test_manual_lifecycle_fast_timeout(self):
        """
        Verify that manual executor lifecycle exits fast on timeout.

        This is the GOOD pattern that we fixed to (Priority 2).
        """
        start = time.time()
        executor = ThreadPoolExecutor(max_workers=1)
        future = None
        try:
            future = executor.submit(time.sleep, 60)  # Slow task
            future.result(timeout=2)  # Timeout after 2s
        except FutureTimeoutError:
            pass  # Expected
        finally:
            if future:
                future.cancel()
            executor.shutdown(wait=False, cancel_futures=True)

        elapsed = time.time() - start

        # Wall-clock proof: must complete in <5s (not 60s!)
        assert elapsed < 5.0, f"Timeout took {elapsed:.2f}s (expected <5s)"
        # Should be very close to timeout value
        assert 1.8 < elapsed < 3.5, f"Timeout was {elapsed:.2f}s (expected ~2s)"

    def test_context_manager_blocks_on_exit(self):
        """
        Demonstrate that `with ThreadPoolExecutor()` blocks even after timeout.

        This is the BAD pattern that we fixed FROM.
        This test documents the bug but doesn't fail (it's just slow).
        """
        start = time.time()
        try:
            with ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(time.sleep, 10)
                future.result(timeout=1)
        except FutureTimeoutError:
            pass

        elapsed = time.time() - start

        # This will take ~10s because context manager waits for worker
        # We don't assert here, just document the behavior
        print(f"Context manager pattern took {elapsed:.2f}s (demonstrates the bug)")

    def test_multiple_workers_fast_cancel(self):
        """
        Test that canceling multiple workers is fast.

        Validates the pattern used in assessment parallel generation.
        """
        start = time.time()
        executor = ThreadPoolExecutor(max_workers=5)
        pending = set()
        try:
            # Submit 5 slow tasks
            for i in range(5):
                pending.add(executor.submit(time.sleep, 60))

            # Immediately cancel all
            for future in pending:
                future.cancel()
        finally:
            executor.shutdown(wait=False, cancel_futures=True)

        elapsed = time.time() - start

        # Should be very fast (just submission + cancellation)
        assert elapsed < 2.0, f"Cancel took {elapsed:.2f}s (expected <2s)"

    def test_partial_results_with_timeout(self):
        """
        Test that we can collect partial results before timeout.

        This is the pattern used in assessment startup fallback.
        """
        from concurrent.futures import wait, FIRST_COMPLETED

        def fast_task(value):
            time.sleep(0.1)
            return value

        def slow_task(value):
            time.sleep(60)
            return value

        start = time.time()
        executor = ThreadPoolExecutor(max_workers=3)
        pending = set()
        results = []

        try:
            # Mix of fast and slow tasks
            pending.add(executor.submit(fast_task, "result1"))
            pending.add(executor.submit(fast_task, "result2"))
            pending.add(executor.submit(slow_task, "result3"))

            deadline = time.time() + 2  # 2s timeout
            while pending and len(results) < 2:
                remaining = deadline - time.time()
                if remaining <= 0:
                    break

                done, pending = wait(pending, timeout=remaining, return_when=FIRST_COMPLETED)
                for future in done:
                    try:
                        result = future.result()
                        results.append(result)
                    except Exception:
                        pass
        finally:
            for future in pending:
                future.cancel()
            executor.shutdown(wait=False, cancel_futures=True)

        elapsed = time.time() - start

        # Should get 2 fast results without waiting for slow task
        assert len(results) == 2, f"Expected 2 results, got {len(results)}"
        assert "result1" in results and "result2" in results
        # Should timeout before slow task (60s)
        assert elapsed < 5.0, f"Took {elapsed:.2f}s (expected <5s)"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
