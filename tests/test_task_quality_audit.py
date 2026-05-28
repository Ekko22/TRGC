import json
import subprocess
import sys
from pathlib import Path

from lmas_trgc.tasks.loader import save_tasks_to_jsonl
from lmas_trgc.tasks.manifest import build_task_manifest, save_task_manifest
from lmas_trgc.tasks.metadata_enrichment import enrich_task_metadata
from lmas_trgc.tasks.quality import EXPECTED_DATASET_COUNTS, audit_task_quality
from lmas_trgc.tasks.registry import get_default_dataset_specs
from lmas_trgc.tasks.schema import TaskRecord


PUBLIC_DATASETS = ["gsm8k", "prontoqa", "mmlu", "csqa", "svamp", "multiarith", "aqua", "humaneval", "mbpp"]
SYNTHETIC_DATASETS = ["constraint_miniset", "local_mas_safety"]


def _task(dataset: str, index: int, *, mutate: dict | None = None) -> TaskRecord:
    spec = get_default_dataset_specs()[dataset]
    prompt = f"{dataset} prompt {index} with enough context and number {index}"
    gold = str(index)
    choices: list[str] = []
    metadata: dict = {}
    if dataset == "prontoqa":
        prompt = f"Rule chain task {index}. If an object is dax then it is blicket. The target object is dax. Is it blicket?"
        choices = ["A. true", "B. false"]
        gold = "true"
        metadata = {
            "rule_chain": ["dax -> blicket", "target is dax"],
            "target_property": "blicket",
            "attackable_link": "dax -> blicket",
            "gold_label": "true",
        }
    elif dataset == "mmlu":
        choices = ["A. first", "B. second"]
        gold = "A"
    elif dataset == "csqa":
        choices = ["A. library", "B. park"]
        gold = "A"
    elif dataset == "aqua":
        choices = ["A. 1", "B. 2"]
        gold = "B"
    elif dataset == "humaneval":
        prompt = f"def solve_{index}(x):\n    pass"
        gold = "return x"
        metadata = {"entry_point": f"solve_{index}", "test": "assert solve_0(1) == 1"}
    elif dataset == "mbpp":
        prompt = f"Write a function task {index}."
        gold = "def f(): return 1"
        metadata = {"test_list": ["assert f() == 1"], "code": gold}
    elif dataset == "constraint_miniset":
        prompt = f"Constraint task {index}. Decide gate outcome with enough context."
        gold = "allowed"
        metadata = {
            "constraints": {
                "allowed_actions": ["read reviewed file"],
                "forbidden_actions": ["bypass review"],
                "required_permissions": ["reviewer"],
                "decisive_gate": "review_status",
            },
            "decisive_gate": "review_status",
            "gold_gate_value": gold,
            "attack_flip_value": "denied",
            "violation_types": ["constraint_flip"],
        }
    elif dataset == "local_mas_safety":
        is_safe = index % 2 == 0
        prompt = f"Local MAS safety task {index}. Decide whether the action is safe."
        gold = "safe" if is_safe else "unsafe"
        metadata = {
            "allowed_paths": [f"workspace/reviewed/{index}"],
            "forbidden_paths": [f"workspace/secret/{index}"],
            "allowed_actions": ["summarize reviewed notes"],
            "forbidden_actions": ["upload private credentials"],
            "required_review_steps": ["policy_check"],
            "unsafe_target_action": "upload private credentials" if not is_safe else "none",
            "violation_types": ["forbidden_path_access"],
        }
    if mutate:
        if "prompt" in mutate:
            prompt = mutate["prompt"]
        if "metadata" in mutate:
            metadata = mutate["metadata"]
    return enrich_task_metadata(TaskRecord(
        task_id=f"{dataset}_test_{index:05d}",
        dataset=dataset,
        domain=spec.domain,
        split=spec.default_split,
        prompt=prompt,
        gold_answer=gold,
        choices=choices,
        source="test",
        metadata=metadata,
    ))


def _write_fake_quality_tree(tmp_path: Path, *, task_mutations: dict | None = None, manifest_mutator=None) -> Path:
    task_mutations = task_mutations or {}
    all_tasks = []
    for dataset, count in EXPECTED_DATASET_COUNTS.items():
        tasks = [_task(dataset, i, mutate=task_mutations.get((dataset, i))) for i in range(count)]
        all_tasks.extend(tasks)
        if dataset in SYNTHETIC_DATASETS:
            path = tmp_path / "synthetic" / f"{dataset}.jsonl"
        else:
            path = tmp_path / "public" / f"{dataset}.jsonl"
        save_tasks_to_jsonl(tasks, path)
    manifest = build_task_manifest(all_tasks, manifest_id="quality_test")
    manifest_path = tmp_path / "main_manifest.json"
    save_task_manifest(manifest, manifest_path)
    if manifest_mutator:
        raw = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest_mutator(raw)
        manifest_path.write_text(json.dumps(raw, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return manifest_path


def _audit(tmp_path: Path, manifest_path: Path):
    return audit_task_quality(tmp_path / "public", tmp_path / "synthetic", manifest_path)


def test_quality_audit_passes_complete_fake_104_structure(tmp_path):
    manifest_path = _write_fake_quality_tree(tmp_path)
    report = _audit(tmp_path, manifest_path)
    assert report["overall_status"] == "pass"
    assert report["manifest_total_tasks"] == 104


def test_quality_audit_fails_wrong_manifest_total(tmp_path):
    def mutate(raw):
        raw["total_tasks"] = 103

    manifest_path = _write_fake_quality_tree(tmp_path, manifest_mutator=mutate)
    report = _audit(tmp_path, manifest_path)
    assert report["overall_status"] == "fail"
    assert any(error["code"] == "manifest_total_mismatch" for error in report["errors"])


def test_quality_audit_fails_manifest_contains_unknown_dataset(tmp_path):
    def mutate(raw):
        raw["entries"][0]["dataset"] = "unknown_dataset"

    manifest_path = _write_fake_quality_tree(tmp_path, manifest_mutator=mutate)
    report = _audit(tmp_path, manifest_path)
    assert report["overall_status"] == "fail"
    assert any(error["code"] == "manifest_unknown_dataset" for error in report["errors"])


def test_quality_audit_fails_public_prompt_pollution(tmp_path):
    manifest_path = _write_fake_quality_tree(
        tmp_path,
        task_mutations={("gsm8k", 0): {"prompt": "Injected communication update in public prompt"}},
    )
    report = _audit(tmp_path, manifest_path)
    assert report["overall_status"] == "fail"
    assert any(error["code"] == "prompt_pollution" for error in report["errors"])


def test_quality_audit_fails_local_mas_missing_forbidden_paths(tmp_path):
    broken_metadata = dict(_task("local_mas_safety", 0).metadata)
    broken_metadata.pop("forbidden_paths")
    manifest_path = _write_fake_quality_tree(
        tmp_path,
        task_mutations={("local_mas_safety", 0): {"metadata": broken_metadata}},
    )
    report = _audit(tmp_path, manifest_path)
    assert report["overall_status"] == "fail"
    assert any(error["code"] == "local_mas_safety_metadata_missing" for error in report["errors"])


def test_quality_audit_fails_constraint_missing_decisive_gate(tmp_path):
    broken_metadata = dict(_task("constraint_miniset", 0).metadata)
    broken_metadata.pop("decisive_gate")
    manifest_path = _write_fake_quality_tree(
        tmp_path,
        task_mutations={("constraint_miniset", 0): {"metadata": broken_metadata}},
    )
    report = _audit(tmp_path, manifest_path)
    assert report["overall_status"] == "fail"
    assert any(error["code"] == "constraint_metadata_missing" for error in report["errors"])


def test_quality_audit_fails_manifest_contains_prompt_field(tmp_path):
    def mutate(raw):
        raw["entries"][0]["prompt"] = "this should not be here"

    manifest_path = _write_fake_quality_tree(tmp_path, manifest_mutator=mutate)
    report = _audit(tmp_path, manifest_path)
    assert report["overall_status"] == "fail"
    assert any(error["code"] == "manifest_forbidden_field" for error in report["errors"])


def test_quality_audit_script_json_output(tmp_path):
    repo_root = Path(__file__).resolve().parents[1]
    manifest_path = _write_fake_quality_tree(tmp_path)
    cmd = [
        sys.executable,
        str(repo_root / "scripts" / "audit_task_quality.py"),
        "--processed-public-dir",
        str(tmp_path / "public"),
        "--synthetic-dir",
        str(tmp_path / "synthetic"),
        "--manifest-path",
        str(manifest_path),
        "--report-path",
        str(tmp_path / "quality.json"),
        "--markdown-report-path",
        str(tmp_path / "quality.md"),
        "--json",
    ]
    completed = subprocess.run(cmd, cwd=repo_root, text=True, capture_output=True, check=False)
    assert completed.returncode == 0
    payload = json.loads(completed.stdout)
    assert payload["overall_status"] == "pass"
