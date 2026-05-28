import pytest

from lmas_trgc.tasks.dataset_sampler import build_main_task_selection, deterministic_sample
from lmas_trgc.tasks.loader import load_dataset_tasks, save_tasks_to_jsonl
from lmas_trgc.tasks.local_synthetic import generate_all_synthetic_tasks, generate_constraint_miniset
from lmas_trgc.tasks.manifest import (
    build_task_manifest,
    load_task_manifest,
    save_task_manifest,
    validate_manifest_counts,
)
from lmas_trgc.tasks.registry import get_default_dataset_specs
from lmas_trgc.tasks.schema import TaskRecord


def test_deterministic_sample_is_stable():
    tasks = generate_constraint_miniset(10)
    first = deterministic_sample(tasks, 4)
    second = deterministic_sample(tasks, 4)
    assert [task.task_id for task in first] == [task.task_id for task in second]


def test_save_load_manifest_roundtrip(tmp_path):
    tasks = generate_constraint_miniset(3)
    manifest = build_task_manifest(tasks, manifest_id="test_manifest")
    path = tmp_path / "manifest.json"
    save_task_manifest(manifest, path)
    loaded = load_task_manifest(path)
    assert loaded.model_dump() == manifest.model_dump()


def test_build_task_manifest_counts_and_no_prompt_field():
    tasks = generate_constraint_miniset(2)
    manifest = build_task_manifest(tasks, manifest_id="test_manifest")
    assert manifest.dataset_counts == {"constraint_miniset": 2}
    dumped = manifest.model_dump()
    assert "prompt" not in str(dumped["entries"])


def test_synthetic_tasks_generate_32_manifest_entries():
    all_tasks = generate_all_synthetic_tasks()
    specs = get_default_dataset_specs()
    selection = build_main_task_selection(all_tasks, specs)
    manifest = build_task_manifest(
        selection.selected_tasks,
        manifest_id="synthetic_only",
        missing_datasets=selection.missing_datasets,
    )
    assert manifest.total_tasks == 32
    assert manifest.dataset_counts["constraint_miniset"] == 16
    assert manifest.dataset_counts["local_mas_safety"] == 16


def test_validate_manifest_counts_passes_and_fails():
    manifest = build_task_manifest(generate_constraint_miniset(2), manifest_id="counts")
    validate_manifest_counts(manifest, {"constraint_miniset": 2})
    with pytest.raises(ValueError):
        validate_manifest_counts(manifest, {"constraint_miniset": 3})


def test_manifest_with_public_gsm8k_and_synthetic_reaches_40(tmp_path):
    public_path = tmp_path / "processed" / "public" / "gsm8k.jsonl"
    public_tasks = [
        TaskRecord(
            task_id=f"gsm8k_test_{idx:05d}",
            dataset="gsm8k",
            domain="math_reasoning",
            split="test",
            prompt=f"What is {idx} + 1?",
            gold_answer=str(idx + 1),
            source="public",
        )
        for idx in range(8)
    ]
    save_tasks_to_jsonl(public_tasks, public_path)

    specs = get_default_dataset_specs()
    specs["gsm8k"] = specs["gsm8k"].model_copy(update={"local_path": str(public_path)})
    all_tasks = generate_all_synthetic_tasks()
    all_tasks["gsm8k"] = load_dataset_tasks(specs["gsm8k"], tmp_path)
    selection = build_main_task_selection(all_tasks, specs)
    manifest = build_task_manifest(selection.selected_tasks, manifest_id="with_public", missing_datasets=selection.missing_datasets)
    assert manifest.total_tasks >= 40
    assert manifest.dataset_counts["gsm8k"] == 8
    assert "mmlu" in manifest.missing_datasets
    assert "prompt" not in str(manifest.model_dump()["entries"])
