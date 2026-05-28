from __future__ import annotations

import os
from typing import Any

from pydantic import BaseModel, Field, field_validator


class HFCandidate(BaseModel):
    path: str
    config: str | None = None
    split: str | None = None

    @field_validator("path")
    @classmethod
    def _path_nonempty(cls, value: str) -> str:
        if not value:
            raise ValueError("HF candidate path must be non-empty")
        return value


class HFAttemptResult(BaseModel):
    candidate: dict[str, Any]
    success: bool
    error_type: str | None = None
    error_message: str | None = None
    row_count: int = 0


class HFDatasetLoadResult(BaseModel):
    success: bool
    dataset_name: str
    items: list[dict] = Field(default_factory=list)
    successful_candidate: dict[str, Any] | None = None
    attempts: list[HFAttemptResult] = Field(default_factory=list)


def _short_error(exc: Exception, limit: int = 500) -> str:
    message = str(exc).replace("\n", " ").strip()
    if len(message) > limit:
        return message[:limit] + "...[truncated]"
    return message


def _dataset_to_dicts(dataset: object, limit: int | None) -> list[dict]:
    items: list[dict] = []
    for index, item in enumerate(dataset):  # type: ignore[operator]
        if limit is not None and index >= limit:
            break
        if not isinstance(item, dict):
            item = dict(item)  # type: ignore[arg-type]
        items.append(dict(item))
    return items


def set_hf_environment_from_args(endpoint: str | None = None, cache_dir: str | None = None) -> None:
    if endpoint:
        os.environ["HF_ENDPOINT"] = endpoint
    if cache_dir:
        os.environ["HF_HOME"] = cache_dir
        os.environ["HF_DATASETS_CACHE"] = cache_dir


def load_hf_with_candidates(
    dataset_name: str,
    candidates: list[dict],
    limit: int | None = None,
) -> HFDatasetLoadResult:
    from datasets import load_dataset

    attempts: list[HFAttemptResult] = []
    for raw_candidate in candidates:
        try:
            candidate = HFCandidate(**raw_candidate)
        except Exception as exc:
            attempts.append(
                HFAttemptResult(
                    candidate=dict(raw_candidate),
                    success=False,
                    error_type=type(exc).__name__,
                    error_message=_short_error(exc),
                )
            )
            continue

        candidate_dict = candidate.model_dump()
        split = candidate.split or "test"
        try:
            if candidate.config:
                loaded = load_dataset(candidate.path, candidate.config, split=split)
            else:
                loaded = load_dataset(candidate.path, split=split)
            items = _dataset_to_dicts(loaded, limit=limit)
        except Exception as exc:
            attempts.append(
                HFAttemptResult(
                    candidate=candidate_dict,
                    success=False,
                    error_type=type(exc).__name__,
                    error_message=_short_error(exc),
                )
            )
            continue

        attempts.append(
            HFAttemptResult(
                candidate=candidate_dict,
                success=True,
                row_count=len(items),
            )
        )
        return HFDatasetLoadResult(
            success=True,
            dataset_name=dataset_name,
            items=items,
            successful_candidate=candidate_dict,
            attempts=attempts,
        )

    return HFDatasetLoadResult(success=False, dataset_name=dataset_name, attempts=attempts)
