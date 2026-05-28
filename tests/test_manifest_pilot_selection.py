import json
from pathlib import Path

import pytest

from lmas_trgc.tasks.loader import save_tasks_to_jsonl
from lmas_trgc.tasks.manifest import build_task_manifest, save_task_manifest
from lmas_trgc.tasks.metadata_enrichment import enrich_task_metadata
from lmas_trgc.tasks.quality import EXPECTED_DATASET_COUNTS
from lmas_trgc.tasks.registry import get_default_dataset_specs
from lmas_trgc.tasks.schema import TaskRecord
from lmas_trgc.runners.manifest_pilot import (
    ManifestPilotTaskSelectionConfig,
    resolve_manifest_task_records,
)


PUBLIC_DATASETS = ["gsm8k", "prontoqa", "mmlu", "csqa", "svamp", "multiarith", "aqua", "humaneval", "mbpp"]
SYNTHETIC_DATASETS = ["constraint_miniset", "local_mas_safety"]


def _task(dataset: str, index: int) -> TaskRecord:
    spec = get_default_dataset_specs()[dataset]
    choices: list[str] = []
    gold = str(index + 1)
    metadata: dict = {}
    prompt = f"{dataset} pilot selection prompt {index} with enough context and number {index + 1}."
    if dataset == "prontoqa":
        prompt = f"Rule chain task {index}. If dax implies blicket and this item is dax, is it blicket?"
        choices = ["A. true", "B. false"]
        gold = "true"
        metadata = {
            "rule_chain": ["dax -> blicket", "item is dax"],
            "target_property": "blicket",
            "attackable_link": "dax -> blicket",
            "gold_label": "true",
        }
    elif dataset in {"mmlu", "csqa", "aqua"}:
        choices = ["A. first", "B. second"]
        gold = "A"
    elif dataset == "humaneval":
        prompt = f"def solve_{index}(x):\n    pass"
        gold = "return x"
        metadata = {"entry_point": f"solve_{index}", "test": "assert solve_0(1) == 1"}
    elif dataset == "mbpp":
        prompt = f"Write a function for pilot selection task {index}."
        gold = "def f(): return 1"
        metadata = {"test_list": ["assert f() == 1"], "code": gold}
    elif dataset == "constraint_miniset":
        gold = "allowed"
        metadata = {
            "decisive_gate": "review_status",
            "gold_gate_value": "allowed",
            "attack_flip_value": "denied",
            "violation_types": ["constraint_flip"],
        }
    elif dataset == "local_mas_safety":
        gold = "safe" if index % 2 == 0 else "unsafe"
        metadata = {
            "allowed_paths": ["workspace/reviewed"],
            "forbidden_paths": ["workspace/secrets"],
            "allowed_actions": ["summarize"],
            "forbidden_actions": ["upload credentials"],
            "unsafe_target_action": "upload credentials",
            "violation_types": ["credential_access"],
        }
    return enrich_task_metadata(
        TaskRecord(
            task_id=f"{dataset}_test_{index:05d}",
            dataset=dataset,
            domain=spec.domain,
            split=spec.default_split,
            prompt=prompt,
            gold_answer=gold,
            choices=choices,
            source="test",
            metadata=metadata,
        )
    )


def _write_fake_manifest_tree(tmp_path: Path) -> Path:
    data_root = tmp_path / "data"
    all_tasks: list[TaskRecord] = []
    for dataset, count in EXPECTED_DATASET_COUNTS.items():
        tasks = [_task(dataset, index) for index in range(count)]
        all_tasks.extend(tasks)
        subdir = "synthetic" if dataset in SYNTHETIC_DATASETS else "public"
        save_tasks_to_jsonl(tasks, data_root / "processed" / subdir / f"{dataset}.jsonl")
    manifest = build_task_manifest(all_tasks, manifest_id="main_v2_104")
    manifest_path = data_root / "manifests" / "main_manifest.json"
    save_task_manifest(manifest, manifest_path)
    return manifest_path


def test_resolve_manifest_task_records_selects_one_per_dataset(tmp_path):
    manifest_path = _write_fake_manifest_tree(tmp_path)
    tasks = resolve_manifest_task_records(ManifestPilotTaskSelectionConfig(manifest_path=str(manifest_path)))
    assert len(tasks) == 11
    assert [task.dataset for task in tasks] == [*PUBLIC_DATASETS, *SYNTHETIC_DATASETS]


def test_resolve_manifest_task_records_supports_dataset_subset(tmp_path):
    manifest_path = _write_fake_manifest_tree(tmp_path)
    tasks = resolve_manifest_task_records(
        ManifestPilotTaskSelectionConfig(manifest_path=str(manifest_path), datasets=["gsm8k", "prontoqa"])
    )
    assert [task.dataset for task in tasks] == ["gsm8k", "prontoqa"]


def test_resolve_manifest_task_records_supports_two_per_dataset(tmp_path):
    manifest_path = _write_fake_manifest_tree(tmp_path)
    tasks = resolve_manifest_task_records(
        ManifestPilotTaskSelectionConfig(manifest_path=str(manifest_path), datasets=["gsm8k", "prontoqa"], tasks_per_dataset=2)
    )
    assert len(tasks) == 4
    assert [task.dataset for task in tasks] == ["gsm8k", "gsm8k", "prontoqa", "prontoqa"]


def test_resolve_manifest_task_records_rejects_manifest_without_prontoqa(tmp_path):
    manifest_path = _write_fake_manifest_tree(tmp_path)
    raw = json.loads(manifest_path.read_text(encoding="utf-8"))
    raw["entries"] = [entry for entry in raw["entries"] if entry["dataset"] != "prontoqa"]
    raw["dataset_counts"].pop("prontoqa")
    raw["total_tasks"] = len(raw["entries"])
    manifest_path.write_text(json.dumps(raw, ensure_ascii=False, indent=2), encoding="utf-8")
    with pytest.raises(ValueError, match="104|dataset_counts|prontoqa"):
        resolve_manifest_task_records(ManifestPilotTaskSelectionConfig(manifest_path=str(manifest_path)))


def test_resolve_manifest_task_records_rejects_wrong_total(tmp_path):
    manifest_path = _write_fake_manifest_tree(tmp_path)
    raw = json.loads(manifest_path.read_text(encoding="utf-8"))
    raw["total_tasks"] = 103
    manifest_path.write_text(json.dumps(raw, ensure_ascii=False, indent=2), encoding="utf-8")
    with pytest.raises(ValueError, match="total_tasks"):
        resolve_manifest_task_records(ManifestPilotTaskSelectionConfig(manifest_path=str(manifest_path)))


def test_resolve_manifest_task_records_rejects_missing_processed_task(tmp_path):
    manifest_path = _write_fake_manifest_tree(tmp_path)
    raw = json.loads(manifest_path.read_text(encoding="utf-8"))
    raw["entries"][0]["task_id"] = "00000_missing_task"
    manifest_path.write_text(json.dumps(raw, ensure_ascii=False, indent=2), encoding="utf-8")
    with pytest.raises(ValueError, match="not found"):
        resolve_manifest_task_records(ManifestPilotTaskSelectionConfig(manifest_path=str(manifest_path)))
