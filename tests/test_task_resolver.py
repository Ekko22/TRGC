import pytest

from lmas_trgc.runners.task_resolver import TaskResolver, TaskResolverConfig


def test_synthetic_resolver_returns_limited_tasks_stably():
    config = TaskResolverConfig(
        mode="synthetic",
        datasets=["local_mas_safety", "constraint_miniset"],
        task_limit_per_dataset=2,
    )
    first = TaskResolver().resolve(config)
    second = TaskResolver().resolve(config)
    assert len(first) == 4
    assert [task.task_id for task in first] == [task.task_id for task in second]


def test_synthetic_resolver_rejects_public_dataset():
    config = TaskResolverConfig(mode="synthetic", datasets=["gsm8k"], task_limit_per_dataset=2)
    with pytest.raises(ValueError):
        TaskResolver().resolve(config)


def test_processed_resolver_missing_file_raises(tmp_path):
    config = TaskResolverConfig(
        mode="processed",
        datasets=["local_mas_safety"],
        processed_root=str(tmp_path),
        task_limit_per_dataset=2,
    )
    with pytest.raises(ValueError):
        TaskResolver().resolve(config)


def test_manifest_resolver_requires_manifest_path():
    config = TaskResolverConfig(mode="manifest", datasets=["local_mas_safety"], task_limit_per_dataset=2)
    with pytest.raises(ValueError):
        TaskResolver().resolve(config)
