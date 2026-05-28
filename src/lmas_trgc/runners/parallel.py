from __future__ import annotations

import re
import sys
from concurrent.futures import Future, ThreadPoolExecutor, as_completed
from collections.abc import Callable
from typing import Any

from pydantic import BaseModel, Field, field_validator
from tqdm import tqdm


class ParallelRunConfig(BaseModel):
    max_workers: int = 1
    show_progress: bool = True
    progress_desc: str = "Running"
    fail_fast: bool = False

    @field_validator("max_workers")
    @classmethod
    def _positive_max_workers(cls, value: int) -> int:
        if value < 1:
            raise ValueError("max_workers must be >= 1")
        return value


class ParallelRunResult(BaseModel):
    run_order: int
    success: bool
    result: dict | None = None
    error: str | None = None
    error_type: str | None = None
    metadata: dict = Field(default_factory=dict)


def safe_error_message(exc: Exception, max_chars: int = 500) -> str:
    message = str(exc) or repr(exc)
    message = re.sub(r"sk-[A-Za-z0-9_\-]+", "[REDACTED]", message)
    message = re.sub(r"github_pat_[A-Za-z0-9_]+", "[REDACTED]", message)
    message = re.sub(r"(?i)authorization\s*[:=]\s*(?:bearer\s+)?[^,\s;]+", "Authorization=[REDACTED]", message)
    message = re.sub(r"(?i)\b(?:api_)?key\s*=\s*[^,\s;]+", "key=[REDACTED]", message)
    if len(message) > max_chars:
        return message[: max_chars - 3] + "..."
    return message


def _failure_result(run_order: int, exc: Exception) -> ParallelRunResult:
    return ParallelRunResult(
        run_order=run_order,
        success=False,
        error=safe_error_message(exc),
        error_type=type(exc).__name__,
    )


def _progress(iterable: Any, config: ParallelRunConfig, total: int) -> Any:
    if not config.show_progress:
        return iterable
    return tqdm(iterable, total=total, desc=config.progress_desc, file=sys.stderr)


def run_parallel_jobs(
    jobs: list[Callable[[], dict]],
    config: ParallelRunConfig,
) -> list[ParallelRunResult]:
    if not jobs:
        return []

    results: list[ParallelRunResult] = []
    if config.max_workers == 1:
        for run_order, job in _progress(enumerate(jobs), config, len(jobs)):
            try:
                results.append(ParallelRunResult(run_order=run_order, success=True, result=job()))
            except Exception as exc:
                if config.fail_fast:
                    raise RuntimeError(
                        f"Parallel job {run_order} failed: {type(exc).__name__}: {safe_error_message(exc)}"
                    ) from exc
                results.append(_failure_result(run_order, exc))
        return sorted(results, key=lambda item: item.run_order)

    executor = ThreadPoolExecutor(max_workers=config.max_workers)
    futures: dict[Future[dict], int] = {
        executor.submit(job): run_order
        for run_order, job in enumerate(jobs)
    }
    try:
        for future in _progress(as_completed(futures), config, len(futures)):
            run_order = futures[future]
            try:
                results.append(ParallelRunResult(run_order=run_order, success=True, result=future.result()))
            except Exception as exc:
                if config.fail_fast:
                    for pending in futures:
                        if pending is not future:
                            pending.cancel()
                    raise RuntimeError(
                        f"Parallel job {run_order} failed: {type(exc).__name__}: {safe_error_message(exc)}"
                    ) from exc
                results.append(_failure_result(run_order, exc))
    finally:
        executor.shutdown(wait=True, cancel_futures=True)
    return sorted(results, key=lambda item: item.run_order)
