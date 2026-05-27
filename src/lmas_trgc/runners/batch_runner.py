from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, Field, field_validator, model_validator

from lmas_trgc.agents.prompt_builder import PromptBuilder
from lmas_trgc.agents.roles import AgentProfile
from lmas_trgc.analysis.batch_aggregate import aggregate_metrics, load_metrics_from_artifact_dirs, metrics_to_rows
from lmas_trgc.attacks.manager import AttackManager
from lmas_trgc.core.ids import stable_hash
from lmas_trgc.defenses.factory import create_defense_adapter
from lmas_trgc.defenses.trgc.safety_verifier import SafetyVerifier
from lmas_trgc.llm.mock_client import MockLLMClient
from lmas_trgc.logging.artifact_writer import RunArtifactWriter
from lmas_trgc.logging.batch_writer import StageBBatchWriter
from lmas_trgc.runners.protocol import ProtocolManager
from lmas_trgc.runners.single_run import SingleRunConfig, SingleRunExecutor
from lmas_trgc.tasks.anchors import build_task_packet
from lmas_trgc.tasks.schema import TaskRecord
from lmas_trgc.topology.manager import TopologyManager


VALID_TOPOLOGIES = {"star", "chain", "graph", "tree"}
VALID_ATTACKS = {"none", "message_poisoning", "role_impersonation", "relay_injection"}
VALID_DEFENSES = {"no_defense", "simple_content_guardrail", "full_checking_light", "gsafeguard", "trgc"}


class StageBBatchConfig(BaseModel):
    batch_id: str
    task_source_mode: str
    datasets: list[str]
    task_limit_per_dataset: int
    topologies: list[str]
    attacks: list[str]
    defenses: list[str]
    output_root: str = "results/runs"
    overwrite: bool = False
    max_steps: int | None = None
    seed: int = 20260527
    use_mock_llm: bool = True

    @field_validator("datasets", "topologies", "attacks", "defenses")
    @classmethod
    def _nonempty_list(cls, value: list[str]) -> list[str]:
        if not value:
            raise ValueError("matrix lists must not be empty")
        return value

    @model_validator(mode="after")
    def _validate_matrix(self) -> "StageBBatchConfig":
        if not self.use_mock_llm:
            raise ValueError("Stage-B batch is mock-only; use_mock_llm must be True")
        invalid_topologies = sorted(set(self.topologies) - VALID_TOPOLOGIES)
        invalid_attacks = sorted(set(self.attacks) - VALID_ATTACKS)
        invalid_defenses = sorted(set(self.defenses) - VALID_DEFENSES)
        if invalid_topologies:
            raise ValueError(f"Unsupported topologies: {invalid_topologies}")
        if invalid_attacks:
            raise ValueError(f"Unsupported attacks: {invalid_attacks}")
        if invalid_defenses:
            raise ValueError(f"Unsupported defenses: {invalid_defenses}")
        return self


class StageBBatchResult(BaseModel):
    batch_id: str
    completed: bool
    total_runs: int
    successful_runs: int
    failed_runs: int
    artifact_dirs: list[str] = Field(default_factory=list)
    failures: list[dict] = Field(default_factory=list)
    aggregate_metrics_path: str | None = None
    run_index_path: str | None = None
    batch_dir: str | None = None


class StageBBatchRunner:
    def __init__(
        self,
        topology_manager: TopologyManager,
        protocol_manager: ProtocolManager,
        agent_profiles: dict[str, AgentProfile],
        prompt_builder: PromptBuilder,
        safety_verifier: SafetyVerifier,
        output_root: str | Path = "results/runs",
    ) -> None:
        self.topology_manager = topology_manager
        self.protocol_manager = protocol_manager
        self.agent_profiles = agent_profiles
        self.prompt_builder = prompt_builder
        self.safety_verifier = safety_verifier
        self.output_root = Path(output_root)

    def _run_id(self, config: StageBBatchConfig, task: TaskRecord, topology: str, attack: str, defense: str) -> str:
        return "run_" + stable_hash(
            "stage_b_batch",
            config.batch_id,
            task.task_id,
            topology,
            attack,
            defense,
            config.seed,
            length=20,
        )

    def run_batch(self, tasks: list[TaskRecord], config: StageBBatchConfig) -> StageBBatchResult:
        output_root = Path(config.output_root or self.output_root)
        batch_writer = StageBBatchWriter(output_root, overwrite=config.overwrite)
        batch_dir = batch_writer.make_batch_dir(config.batch_id)
        artifact_writer = RunArtifactWriter(output_root, stage_name="stage_b", overwrite=config.overwrite)

        run_records: list[dict] = []
        failures: list[dict] = []
        artifact_dirs: list[str] = []
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
                        }
                        try:
                            defense_adapter = create_defense_adapter(
                                defense,
                                self.topology_manager,
                                safety_verifier=self.safety_verifier,
                            )
                            executor = SingleRunExecutor(
                                topology_manager=self.topology_manager,
                                protocol_manager=self.protocol_manager,
                                agent_profiles=self.agent_profiles,
                                defense_adapter=defense_adapter,
                                llm_clients_by_agent={
                                    agent_id: MockLLMClient(model_name=f"mock-{agent_id}")
                                    for agent_id in self.agent_profiles
                                },
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
                                    use_mock_llm=True,
                                    max_steps=config.max_steps,
                                ),
                            )
                            manifest = artifact_writer.write_run_artifact(
                                result,
                                task_packet,
                                config_snapshot={
                                    "stage": "stage_b_batch",
                                    "batch_id": config.batch_id,
                                    "task_source_mode": config.task_source_mode,
                                    "dataset": task.dataset,
                                    "topology": topology,
                                    "attack": attack,
                                    "defense": defense,
                                    "max_steps": config.max_steps,
                                    "use_mock_llm": True,
                                },
                            )
                            record["artifact_dir"] = manifest.artifact_dir
                            record["completed"] = result.completed
                            artifact_dirs.append(manifest.artifact_dir)
                        except Exception as exc:
                            record["failed"] = True
                            record["error"] = f"{type(exc).__name__}: {exc}"
                            failures.append(dict(record))
                        run_records.append(record)

        metrics = load_metrics_from_artifact_dirs(artifact_dirs)
        aggregate = aggregate_metrics(metrics)
        rows = metrics_to_rows(metrics)
        summary = {
            "batch_id": config.batch_id,
            "completed": len(failures) == 0,
            "total_runs": total_runs,
            "successful_runs": len(artifact_dirs),
            "failed_runs": len(failures),
            "artifact_count": len(artifact_dirs),
            "task_count": len(tasks),
            "datasets": config.datasets,
            "topologies": config.topologies,
            "attacks": config.attacks,
            "defenses": config.defenses,
        }

        run_index_path = batch_writer.write_run_index(batch_dir, run_records)
        batch_writer.write_batch_summary(batch_dir, summary)
        aggregate_json_path, _ = batch_writer.write_aggregate_metrics(batch_dir, aggregate, rows)
        batch_writer.write_readme(batch_dir, summary)
        batch_writer.write_manifest(
            batch_dir,
            files={
                "batch_summary": "batch_summary.json",
                "run_index": "run_index.jsonl",
                "aggregate_metrics_json": "aggregate_metrics.json",
                "aggregate_metrics_csv": "aggregate_metrics.csv",
                "readme": "README.md",
            },
            metadata={"batch_id": config.batch_id, "schema": "stage_b_batch"},
        )

        return StageBBatchResult(
            batch_id=config.batch_id,
            completed=len(failures) == 0,
            total_runs=total_runs,
            successful_runs=len(artifact_dirs),
            failed_runs=len(failures),
            artifact_dirs=artifact_dirs,
            failures=failures,
            aggregate_metrics_path=str(aggregate_json_path),
            run_index_path=str(run_index_path),
            batch_dir=str(batch_dir),
        )
