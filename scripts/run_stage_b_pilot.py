#!/usr/bin/env python
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from lmas_trgc.agents.prompt_builder import PromptBuilder
from lmas_trgc.agents.roles import load_agent_profiles
from lmas_trgc.attacks.manager import AttackManager
from lmas_trgc.core.ids import make_run_id
from lmas_trgc.defenses.factory import create_defense_adapter
from lmas_trgc.defenses.trgc.safety_verifier import SafetyVerifier
from lmas_trgc.analysis.run_summary import build_run_summary_record
from lmas_trgc.analysis.standard_metrics import build_standard_run_metrics
from lmas_trgc.judging.judge import create_judge
from lmas_trgc.logging.artifact_writer import RunArtifactWriter
from lmas_trgc.llm.mock_client import MockLLMClient
from lmas_trgc.runners.protocol import ProtocolManager
from lmas_trgc.runners.single_run import SingleRunConfig, SingleRunExecutor
from lmas_trgc.tasks.anchors import build_task_packet
from lmas_trgc.tasks.local_synthetic import generate_constraint_miniset, generate_local_mas_safety_set
from lmas_trgc.topology.manager import TopologyManager


def _task_for(dataset: str, index: int):
    if dataset == "local_mas_safety":
        tasks = generate_local_mas_safety_set(16)
    elif dataset == "constraint_miniset":
        tasks = generate_constraint_miniset(16)
    else:
        raise ValueError(f"Stage-B pilot only supports synthetic datasets, got: {dataset}")
    if index < 0 or index >= len(tasks):
        raise IndexError(f"task-index {index} out of range for {dataset}; available 0..{len(tasks)-1}")
    return tasks[index]


def _summary(result, artifact_dir: str | None = None, judge_outcome=None) -> dict:
    judge_fields = {}
    if judge_outcome is not None:
        judge_fields = {
            "judge_mode": judge_outcome.judge_mode,
            "valid_for_paper": judge_outcome.valid_for_paper,
            "task_success": judge_outcome.task_success,
            "attack_success": judge_outcome.attack_success,
            "safety_violation": judge_outcome.safety_violation,
            "robust_success": judge_outcome.robust_success,
        }
    return {
        "run_id": result.run_id,
        "task_id": result.task_id,
        "topology": result.topology,
        "defense": result.defense_name,
        "attack": result.attack_type,
        "total_messages": result.total_messages,
        "attacked_messages": result.attacked_messages,
        "delivered_messages": result.delivered_messages,
        "blocked_messages": result.blocked_messages,
        "downweighted_messages": result.downweighted_messages,
        "rerouted_messages": result.rerouted_messages,
        "completed": result.completed,
        "artifact_dir": artifact_dir,
        **judge_fields,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Run mock-only Stage-B pilot with communication attacks.")
    parser.add_argument("--topology", choices=["star", "chain", "graph", "tree"], default="graph")
    parser.add_argument("--defense", default="trgc")
    parser.add_argument(
        "--attack",
        choices=["none", "message_poisoning", "role_impersonation", "relay_injection"],
        default="message_poisoning",
    )
    parser.add_argument("--dataset", choices=["local_mas_safety", "constraint_miniset"], default="local_mas_safety")
    parser.add_argument("--task-index", type=int, default=0)
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--max-steps", type=int)
    parser.add_argument("--output-root", default="results/runs")
    parser.add_argument("--save-artifact", action="store_true")
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--judge-mode", choices=["mock_protocol", "rule_based"], default="mock_protocol")
    args = parser.parse_args()
    try:
        task = _task_for(args.dataset, args.task_index)
        run_id = make_run_id(
            stage="stage_b_pilot",
            topology=args.topology,
            attack=args.attack,
            defense=args.defense,
            seed=20260527,
            task_id=task.task_id,
        )
        if args.dry_run:
            output = {
                "run_id": run_id,
                "task_id": task.task_id,
                "topology": args.topology,
                "defense": args.defense,
                "attack": args.attack,
                "dataset": args.dataset,
                "dry_run": True,
                "artifact_dir": None,
                "judge_mode": args.judge_mode,
            }
            print(json.dumps(output, indent=2) if args.json else output)
            return 0

        topology_manager = TopologyManager()
        profiles = load_agent_profiles()
        verifier = SafetyVerifier(mode="mock")
        adapter = create_defense_adapter(args.defense, topology_manager, safety_verifier=verifier)
        executor = SingleRunExecutor(
            topology_manager=topology_manager,
            protocol_manager=ProtocolManager(topology_manager=topology_manager),
            agent_profiles=profiles,
            defense_adapter=adapter,
            llm_clients_by_agent={agent_id: MockLLMClient(model_name=f"mock-{agent_id}") for agent_id in profiles},
            prompt_builder=PromptBuilder(),
            attack_manager=AttackManager(args.attack),
        )
        result = executor.run(
            task_packet := build_task_packet(task),
            SingleRunConfig(
                run_id=run_id,
                topology=args.topology,
                attack_type=args.attack,
                defense_name=args.defense,
                use_mock_llm=True,
                max_steps=args.max_steps,
            ),
        )
        artifact_dir = None
        judge = create_judge(args.judge_mode)
        judge_outcome = judge.judge(result, task_packet)
        standard_metrics = build_standard_run_metrics(build_run_summary_record(result, task_packet), judge_outcome)
        if args.save_artifact:
            writer = RunArtifactWriter(args.output_root, stage_name="stage_b", overwrite=args.overwrite)
            manifest = writer.write_run_artifact(
                result,
                task_packet,
                config_snapshot={
                    "stage": "stage_b",
                    "topology": args.topology,
                    "defense": args.defense,
                    "attack": args.attack,
                    "dataset": args.dataset,
                    "task_index": args.task_index,
                    "max_steps": args.max_steps,
                    "use_mock_llm": True,
                    "save_artifact": args.save_artifact,
                    "judge_mode": args.judge_mode,
                },
                judge_outcome=judge_outcome,
                standard_metrics=standard_metrics,
            )
            artifact_dir = manifest.artifact_dir
        summary = _summary(result, artifact_dir=artifact_dir, judge_outcome=judge_outcome)
        print(json.dumps(summary, indent=2) if args.json else summary)
        return 0
    except Exception as exc:
        if args.json:
            print(json.dumps({"ok": False, "error": type(exc).__name__, "message": str(exc)}))
        else:
            print(f"Stage-B pilot failed: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
