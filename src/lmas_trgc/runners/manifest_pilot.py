from __future__ import annotations

from collections import defaultdict
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field, field_validator, model_validator

from lmas_trgc.agents.prompt_builder import PromptBuilder
from lmas_trgc.agents.roles import AgentProfile
from lmas_trgc.analysis.batch_aggregate import aggregate_metrics, load_metrics_from_artifact_dirs, metrics_to_rows
from lmas_trgc.analysis.effect_aggregate import aggregate_standard_metrics
from lmas_trgc.analysis.run_summary import build_run_summary_record
from lmas_trgc.analysis.standard_metrics import StandardRunMetrics, build_standard_run_metrics
from lmas_trgc.attacks.manager import AttackManager
from lmas_trgc.core.ids import stable_hash
from lmas_trgc.defenses.factory import create_defense_adapter
from lmas_trgc.defenses.trgc.safety_verifier import SafetyVerifier
from lmas_trgc.judging.judge import create_judge
from lmas_trgc.llm.factory import (
    build_deepseek_client_from_registry,
    build_safety_verifier_from_registry,
    build_single_model_agent_clients,
    check_deepseek_configuration,
)
from lmas_trgc.llm.registry import ModelRegistry
from lmas_trgc.logging.artifact_writer import RunArtifactWriter
from lmas_trgc.logging.batch_writer import StageBBatchWriter
from lmas_trgc.runners.protocol import ProtocolManager
from lmas_trgc.runners.single_run import SingleRunConfig, SingleRunExecutor
from lmas_trgc.tasks.anchors import build_task_packet
from lmas_trgc.tasks.loader import load_tasks_from_jsonl
from lmas_trgc.tasks.manifest import TaskManifest, load_task_manifest
from lmas_trgc.tasks.quality import ACTIVE_DATASETS, EXPECTED_DATASET_COUNTS, EXPECTED_MANIFEST_ID, EXPECTED_TOTAL_TASKS
from lmas_trgc.tasks.schema import TaskRecord
from lmas_trgc.topology.manager import TopologyManager

VALID_TOPOLOGIES = {"star", "chain", "graph", "tree"}
VALID_ATTACKS = {"none", "message_poisoning", "role_impersonation", "relay_injection"}
VALID_DEFENSES = {"no_defense", "simple_content_guardrail", "full_checking_light", "trgc"}
VALID_SV_MODES = {"mock", "client"}
VALID_JUDGE_MODES = {"rule_based", "mock_protocol"}
SYNTHETIC_DATASETS = {"constraint_miniset", "local_mas_safety"}


class ManifestPilotTaskSelectionConfig(BaseModel):
    manifest_path: str = "data/manifests/main_manifest.json"
    tasks_per_dataset: int = 1
    datasets: list[str] = Field(default_factory=list)
    seed: int = 20260527

    @field_validator("tasks_per_dataset")
    @classmethod
    def _positive_tasks_per_dataset(cls, value: int) -> int:
        if value < 1:
            raise ValueError("tasks_per_dataset must be >= 1")
        return value

    @field_validator("datasets")
    @classmethod
    def _valid_dataset_subset(cls, value: list[str]) -> list[str]:
        invalid = sorted(set(value) - set(ACTIVE_DATASETS))
        if invalid:
            raise ValueError(f"datasets must be active main datasets; unsupported: {invalid}")
        return value


class StageCDeepSeekManifestPilotConfig(BaseModel):
    batch_id: str
    manifest_path: str = "data/manifests/main_manifest.json"
    tasks_per_dataset: int = 1
    datasets: list[str] = Field(default_factory=list)
    topologies: list[str] = Field(default_factory=lambda: ["graph"])
    attacks: list[str] = Field(default_factory=lambda: ["message_poisoning"])
    defenses: list[str] = Field(default_factory=lambda: ["no_defense", "trgc"])
    max_steps: int = 3
    sv_mode: str = "client"
    allow_sv_mock_fallback: bool = False
    judge_mode: str = "rule_based"
    output_root: str = "results/runs"
    overwrite: bool = False
    confirm_real_llm: bool = False
    require_deepseek_key: bool = True
    require_sv_key: bool = False
    seed: int = 20260527
    warnings: list[str] = Field(default_factory=list)

    @field_validator("tasks_per_dataset", "max_steps")
    @classmethod
    def _positive_int(cls, value: int) -> int:
        if value < 1:
            raise ValueError("tasks_per_dataset and max_steps must be >= 1")
        return value

    @model_validator(mode="after")
    def _validate_matrix(self) -> "StageCDeepSeekManifestPilotConfig":
        if not self.batch_id.strip():
            raise ValueError("batch_id must not be empty")
        invalid_datasets = sorted(set(self.datasets) - set(ACTIVE_DATASETS))
        invalid_topologies = sorted(set(self.topologies) - VALID_TOPOLOGIES)
        invalid_attacks = sorted(set(self.attacks) - VALID_ATTACKS)
        invalid_defenses = sorted(set(self.defenses) - VALID_DEFENSES)
        if invalid_datasets:
            raise ValueError(f"Unsupported datasets: {invalid_datasets}")
        if invalid_topologies:
            raise ValueError(f"Unsupported topologies: {invalid_topologies}")
        if invalid_attacks:
            raise ValueError(f"Unsupported attacks: {invalid_attacks}")
        if invalid_defenses:
            raise ValueError(f"Unsupported defenses: {invalid_defenses}")
        if not self.topologies:
            raise ValueError("topologies must not be empty")
        if not self.attacks:
            raise ValueError("attacks must not be empty")
        if not self.defenses:
            raise ValueError("defenses must not be empty")
        if self.sv_mode not in VALID_SV_MODES:
            raise ValueError("sv_mode must be mock or client")
        if self.judge_mode not in VALID_JUDGE_MODES:
            raise ValueError("judge_mode must be rule_based or mock_protocol")
        if any(attack != "none" for attack in self.attacks) and self.max_steps < 3:
            self.warnings.append("max_steps < 3 may not reach high-value graph attack edges")
        return self


class StageCDeepSeekManifestPilotResult(BaseModel):
    batch_id: str
    completed: bool
    total_runs: int
    successful_runs: int
    failed_runs: int
    selected_tasks: int
    selected_datasets: list[str]
    total_messages: int
    total_attacked_messages: int
    total_llm_calls: int
    total_tokens: int
    batch_dir: str | None = None
    run_index_path: str | None = None
    aggregate_metrics_path: str | None = None
    standard_metrics_path: str | None = None
    artifact_dirs: list[str] = Field(default_factory=list)
    failures: list[dict] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


def _processed_root_for_manifest(manifest_path: Path) -> Path:
    manifest_path = Path(manifest_path)
    if manifest_path.parent.name == "manifests":
        return manifest_path.parent.parent / "processed"
    return Path("data/processed")


def _validate_manifest(manifest: TaskManifest) -> None:
    if manifest.manifest_id != EXPECTED_MANIFEST_ID:
        raise ValueError(f"Manifest must be {EXPECTED_MANIFEST_ID}, got {manifest.manifest_id}")
    if manifest.total_tasks != EXPECTED_TOTAL_TASKS:
        raise ValueError(f"Manifest total_tasks must be {EXPECTED_TOTAL_TASKS}, got {manifest.total_tasks}")
    if manifest.missing_datasets:
        raise ValueError(f"Manifest missing_datasets must be empty, got {manifest.missing_datasets}")
    if manifest.dataset_counts != EXPECTED_DATASET_COUNTS:
        raise ValueError(f"Manifest dataset_counts mismatch: {manifest.dataset_counts}")
    if set(manifest.dataset_counts) != set(ACTIVE_DATASETS):
        raise ValueError("Manifest must contain exactly the active 104-task datasets, including prontoqa")
    if "prontoqa" not in manifest.dataset_counts:
        raise ValueError("Manifest must include prontoqa")


def load_processed_task_index(processed_root: Path = Path("data/processed")) -> dict[tuple[str, str], TaskRecord]:
    index: dict[tuple[str, str], TaskRecord] = {}
    for dataset in ACTIVE_DATASETS:
        subdir = "synthetic" if dataset in SYNTHETIC_DATASETS else "public"
        path = Path(processed_root) / subdir / f"{dataset}.jsonl"
        if not path.exists():
            raise ValueError(f"Processed dataset {dataset!r} is missing at {path}")
        for task in load_tasks_from_jsonl(path):
            index[(task.dataset, task.task_id)] = task
    return index


def resolve_manifest_task_records(selection_config: ManifestPilotTaskSelectionConfig) -> list[TaskRecord]:
    manifest_path = Path(selection_config.manifest_path)
    manifest = load_task_manifest(manifest_path)
    _validate_manifest(manifest)
    dataset_order = selection_config.datasets or list(ACTIVE_DATASETS)
    processed_root = _processed_root_for_manifest(manifest_path)
    task_index = load_processed_task_index(processed_root)

    entries_by_dataset: dict[str, list[Any]] = defaultdict(list)
    for entry in manifest.entries:
        if entry.selected:
            entries_by_dataset[entry.dataset].append(entry)

    selected: list[TaskRecord] = []
    for dataset in dataset_order:
        entries = sorted(entries_by_dataset.get(dataset, []), key=lambda entry: entry.task_id)
        if len(entries) < selection_config.tasks_per_dataset:
            raise ValueError(
                f"Dataset {dataset!r} has {len(entries)} selected manifest entries; "
                f"need {selection_config.tasks_per_dataset}"
            )
        for entry in entries[: selection_config.tasks_per_dataset]:
            task = task_index.get((entry.dataset, entry.task_id))
            if task is None:
                raise ValueError(f"Manifest task {entry.dataset}/{entry.task_id} was not found in processed JSONL")
            selected.append(task)
    return selected


class StageCDeepSeekManifestPilotRunner:
    def __init__(
        self,
        topology_manager: TopologyManager,
        protocol_manager: ProtocolManager,
        agent_profiles: dict[str, AgentProfile],
        prompt_builder: PromptBuilder,
        model_registry: ModelRegistry,
        output_root: str | Path = "results/runs",
    ) -> None:
        self.topology_manager = topology_manager
        self.protocol_manager = protocol_manager
        self.agent_profiles = agent_profiles
        self.prompt_builder = prompt_builder
        self.model_registry = model_registry
        self.output_root = Path(output_root)

    def _run_id(self, config: StageCDeepSeekManifestPilotConfig, task: TaskRecord, topology: str, attack: str, defense: str) -> str:
        return "run_" + stable_hash(
            "stage_c_manifest",
            config.batch_id,
            task.task_id,
            topology,
            attack,
            defense,
            config.max_steps,
            config.seed,
            length=20,
        )

    def _build_safety_verifier(self, config: StageCDeepSeekManifestPilotConfig, warnings: list[str]) -> SafetyVerifier:
        if config.sv_mode == "mock":
            warnings.append("sv_mode=mock; local SV client was not used")
            return build_safety_verifier_from_registry(self.model_registry, mode="mock", require_key=False)
        sv_missing = check_deepseek_configuration(self.model_registry, require_sv=True)
        sv_missing = [item for item in sv_missing if item.startswith("SV ")]
        if sv_missing:
            if config.allow_sv_mock_fallback:
                warnings.append(f"SV client config incomplete; using mock fallback: {sv_missing}")
                return build_safety_verifier_from_registry(self.model_registry, mode="mock", require_key=False)
            raise RuntimeError(f"SV client configuration is incomplete: {sv_missing}")
        return build_safety_verifier_from_registry(self.model_registry, mode="client", require_key=True)

    def run_pilot(self, config: StageCDeepSeekManifestPilotConfig) -> StageCDeepSeekManifestPilotResult:
        if not config.confirm_real_llm:
            raise RuntimeError("Refusing to run real DeepSeek manifest pilot without --confirm-real-llm")
        missing = check_deepseek_configuration(self.model_registry, require_sv=False)
        if missing:
            raise RuntimeError(f"DeepSeek M1 configuration is incomplete: {missing}")

        warnings = list(config.warnings)
        tasks = resolve_manifest_task_records(
            ManifestPilotTaskSelectionConfig(
                manifest_path=config.manifest_path,
                tasks_per_dataset=config.tasks_per_dataset,
                datasets=config.datasets,
                seed=config.seed,
            )
        )
        selected_datasets = []
        for task in tasks:
            if task.dataset not in selected_datasets:
                selected_datasets.append(task.dataset)

        output_root = Path(config.output_root or self.output_root)
        batch_writer = StageBBatchWriter(output_root, overwrite=config.overwrite, batch_stage_name="stage_c_manifest_batches")
        batch_dir = batch_writer.make_batch_dir(config.batch_id)
        artifact_writer = RunArtifactWriter(output_root, stage_name="stage_c_manifest", overwrite=config.overwrite)

        deepseek_client = build_deepseek_client_from_registry(self.model_registry, require_key=config.require_deepseek_key)
        agent_clients = build_single_model_agent_clients(self.agent_profiles, deepseek_client)
        safety_verifier = self._build_safety_verifier(config, warnings)
        judge = create_judge(config.judge_mode)

        run_records: list[dict] = []
        failures: list[dict] = []
        artifact_dirs: list[str] = []
        standard_metric_records: list[StandardRunMetrics] = []
        standard_metric_rows: list[dict] = []
        total_runs = len(tasks) * len(config.topologies) * len(config.attacks) * len(config.defenses)

        for task in tasks:
            task_packet = build_task_packet(task)
            for topology in config.topologies:
                for attack in config.attacks:
                    for defense in config.defenses:
                        run_id = self._run_id(config, task, topology, attack, defense)
                        record = {
                            "batch_id": config.batch_id,
                            "run_id": run_id,
                            "task_id": task.task_id,
                            "dataset": task.dataset,
                            "topology": topology,
                            "attack": attack,
                            "defense": defense,
                            "artifact_dir": None,
                            "completed": False,
                            "failed": False,
                            "error": None,
                            "judge_mode": config.judge_mode,
                            "valid_for_paper": None,
                            "task_success": None,
                            "attack_success": None,
                            "safety_violation": None,
                            "robust_success": None,
                        }
                        try:
                            defense_adapter = create_defense_adapter(
                                defense,
                                self.topology_manager,
                                safety_verifier=safety_verifier,
                            )
                            executor = SingleRunExecutor(
                                topology_manager=self.topology_manager,
                                protocol_manager=self.protocol_manager,
                                agent_profiles=self.agent_profiles,
                                defense_adapter=defense_adapter,
                                llm_clients_by_agent=agent_clients,
                                prompt_builder=self.prompt_builder,
                                attack_manager=AttackManager(attack),
                            )
                            result = executor.run(
                                task_packet,
                                SingleRunConfig(
                                    run_id=run_id,
                                    topology=topology,
                                    attack_type=attack,
                                    defense_name=defense,
                                    use_mock_llm=False,
                                    max_steps=config.max_steps,
                                ),
                            )
                            judge_outcome = judge.judge(result, task_packet)
                            run_summary = build_run_summary_record(result, task_packet)
                            standard_metrics = build_standard_run_metrics(run_summary, judge_outcome)
                            manifest = artifact_writer.write_run_artifact(
                                result,
                                task_packet,
                                config_snapshot={
                                    "stage": "stage_c_deepseek_manifest_pilot",
                                    "batch_id": config.batch_id,
                                    "manifest_path": config.manifest_path,
                                    "manifest_id": EXPECTED_MANIFEST_ID,
                                    "task_id": task.task_id,
                                    "dataset": task.dataset,
                                    "topology": topology,
                                    "attack": attack,
                                    "defense": defense,
                                    "max_steps": config.max_steps,
                                    "sv_mode": config.sv_mode,
                                    "judge_mode": config.judge_mode,
                                    "task_agent_model_slot": "M1",
                                    "task_agent_model_name": self.model_registry.get_task_model("M1").model_name,
                                },
                                judge_outcome=judge_outcome,
                                standard_metrics=standard_metrics,
                            )
                            record["artifact_dir"] = manifest.artifact_dir
                            record["completed"] = result.completed
                            record["valid_for_paper"] = judge_outcome.valid_for_paper
                            record["task_success"] = judge_outcome.task_success
                            record["attack_success"] = judge_outcome.attack_success
                            record["safety_violation"] = judge_outcome.safety_violation
                            record["robust_success"] = judge_outcome.robust_success
                            artifact_dirs.append(manifest.artifact_dir)
                            standard_metric_records.append(standard_metrics)
                            standard_metric_rows.append(standard_metrics.model_dump(mode="json"))
                        except Exception as exc:
                            record["failed"] = True
                            record["error"] = f"{type(exc).__name__}: {exc}"
                            failures.append(dict(record))
                        run_records.append(record)

        metrics = load_metrics_from_artifact_dirs(artifact_dirs)
        aggregate = aggregate_metrics(metrics)
        rows = metrics_to_rows(metrics)
        standard_effect = aggregate_standard_metrics(standard_metric_records)
        summary = {
            "batch_id": config.batch_id,
            "stage": "stage_c_deepseek_manifest_pilot",
            "completed": len(failures) == 0,
            "total_runs": total_runs,
            "successful_runs": len(artifact_dirs),
            "failed_runs": len(failures),
            "artifact_count": len(artifact_dirs),
            "selected_tasks": len(tasks),
            "selected_datasets": selected_datasets,
            "topologies": config.topologies,
            "attacks": config.attacks,
            "defenses": config.defenses,
            "max_steps": config.max_steps,
            "sv_mode": config.sv_mode,
            "judge_mode": config.judge_mode,
            "total_messages": aggregate.get("total_messages", 0),
            "total_attacked_messages": aggregate.get("total_attacked_messages", 0),
            "total_llm_calls": aggregate.get("total_llm_calls", 0),
            "total_tokens": aggregate.get("total_tokens", 0),
            "warnings": warnings,
        }
        run_index_path = batch_writer.write_run_index(batch_dir, run_records)
        batch_writer.write_batch_summary(batch_dir, summary)
        aggregate_json_path, _ = batch_writer.write_aggregate_metrics(batch_dir, aggregate, rows)
        standard_effect_json_path, _ = batch_writer.write_standard_effect_metrics(
            batch_dir,
            standard_effect,
            standard_metric_rows,
        )
        batch_writer.write_readme(batch_dir, summary)
        batch_writer.write_manifest(
            batch_dir,
            files={
                "batch_summary": "batch_summary.json",
                "run_index": "run_index.jsonl",
                "aggregate_metrics_json": "aggregate_metrics.json",
                "aggregate_metrics_csv": "aggregate_metrics.csv",
                "standard_effect_metrics_json": "standard_effect_metrics.json",
                "standard_effect_metrics_csv": "standard_effect_metrics.csv",
                "readme": "README.md",
            },
            metadata={"batch_id": config.batch_id, "schema": "stage_c_deepseek_manifest_pilot"},
        )

        return StageCDeepSeekManifestPilotResult(
            batch_id=config.batch_id,
            completed=len(failures) == 0,
            total_runs=total_runs,
            successful_runs=len(artifact_dirs),
            failed_runs=len(failures),
            selected_tasks=len(tasks),
            selected_datasets=selected_datasets,
            total_messages=int(aggregate.get("total_messages", 0)),
            total_attacked_messages=int(aggregate.get("total_attacked_messages", 0)),
            total_llm_calls=int(aggregate.get("total_llm_calls", 0)),
            total_tokens=int(aggregate.get("total_tokens", 0)),
            batch_dir=str(batch_dir),
            run_index_path=str(run_index_path),
            aggregate_metrics_path=str(aggregate_json_path),
            standard_metrics_path=str(standard_effect_json_path),
            artifact_dirs=artifact_dirs,
            failures=failures,
            warnings=warnings,
        )
