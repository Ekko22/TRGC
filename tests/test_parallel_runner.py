import threading
import time

import pytest

from lmas_trgc.runners.parallel import ParallelRunConfig, run_parallel_jobs, safe_error_message


def test_parallel_jobs_max_workers_one_preserves_order():
    jobs = [lambda index=index: {"index": index} for index in range(3)]
    results = run_parallel_jobs(jobs, ParallelRunConfig(max_workers=1, show_progress=False))
    assert [item.run_order for item in results] == [0, 1, 2]
    assert [item.result["index"] for item in results if item.result] == [0, 1, 2]


def test_parallel_jobs_max_workers_two_runs_concurrently():
    active = 0
    max_active = 0
    lock = threading.Lock()

    def job() -> dict:
        nonlocal active, max_active
        with lock:
            active += 1
            max_active = max(max_active, active)
        time.sleep(0.05)
        with lock:
            active -= 1
        return {"ok": True}

    results = run_parallel_jobs([job for _ in range(4)], ParallelRunConfig(max_workers=2, show_progress=False))
    assert all(item.success for item in results)
    assert max_active >= 2


def test_parallel_jobs_failure_does_not_block_other_jobs_when_not_fail_fast():
    def boom() -> dict:
        raise RuntimeError("service failed with sk-secret123 key=secret")

    jobs = [lambda: {"index": 0}, boom, lambda: {"index": 2}]
    results = run_parallel_jobs(jobs, ParallelRunConfig(max_workers=2, show_progress=False, fail_fast=False))
    assert [item.run_order for item in results] == [0, 1, 2]
    assert results[0].success is True
    assert results[1].success is False
    assert results[1].error_type == "RuntimeError"
    assert "service failed" in results[1].error
    assert "[REDACTED]" in results[1].error
    assert results[2].success is True


def test_parallel_jobs_fail_fast_raises_runtime_error():
    def boom() -> dict:
        raise ValueError("bad job")

    with pytest.raises(RuntimeError, match="Parallel job"):
        run_parallel_jobs([boom, lambda: {"ok": True}], ParallelRunConfig(max_workers=2, show_progress=False, fail_fast=True))


def test_safe_error_message_redacts_keys_and_truncates():
    message = safe_error_message(
        RuntimeError("sk-abc123 key=super-secret Authorization=BearerToken " + ("x" * 200)),
        max_chars=80,
    )
    assert "sk-abc123" not in message
    assert "super-secret" not in message
    assert "BearerToken" not in message
    assert "[REDACTED]" in message
    assert len(message) <= 80


def test_parallel_jobs_results_sorted_by_run_order():
    def job(index: int, delay: float) -> dict:
        time.sleep(delay)
        return {"index": index}

    jobs = [
        lambda: job(0, 0.03),
        lambda: job(1, 0.01),
        lambda: job(2, 0.02),
    ]
    results = run_parallel_jobs(jobs, ParallelRunConfig(max_workers=3, show_progress=False))
    assert [item.run_order for item in results] == [0, 1, 2]
    assert [item.result["index"] for item in results if item.result] == [0, 1, 2]
