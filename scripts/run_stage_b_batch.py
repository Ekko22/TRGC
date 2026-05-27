#!/usr/bin/env python
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from lmas_trgc.agents.prompt_builder import PromptBuilder
from lmas_trgc.agents.roles import load_agent_profiles
from lmas_trgc.core.ids import stable_hash
from lmas_trgc.defenses.trgc.safety_verifier import SafetyVerifier
from lmas_trgc.runners.batch_runner import StageBBatchConfig, StageBBatchRunner
from lmas_trgc.runners.protocol import ProtocolManager
from lmas_trgc.runners.task_resolver import TaskResolver, TaskResolverConfig
from lmas_trgc.topology.manager import TopologyManager


def _split_csv(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


def _default_batch_id(args: argparse.Namespace) -> str:
    return "batch_" + stable_hash(
        "stage_b_batch",
        args.task_source_mode,
        args.datasets,
        args.task_limit_per_dataset,
        args.topologies,
        args.attacks,
        args.defenses,
        args.max_steps,
        length=16,
    )


def _summary(result) -> dict:
    return {
        "batch_id": result.batch_id,
        "completed": result.completed,
        "total_runs": result.total_runs,
        "successful_runs": result.successful_runs,
        "failed_runs": result.failed_runs,
        "batch_dir": result.batch_dir,
        "run_index_path": result.run_index_path,
        "aggregate_metrics_path": result.aggregate_metrics_path,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Run mock-only Stage-B batch experiments.")
    parser.add_argument("--batch-id")
    parser.add_argument("--task-source-mode", choices=["synthetic", "processed", "manifest"], default="synthetic")
    parser.add_argument("--datasets", default="local_mas_safety,constraint_miniset")
    parser.add_argument("--task-limit-per-dataset", type=int, default=2)
    parser.add_argument("--manifest-path")
    parser.add_argument("--topologies", default="graph")
    parser.add_argument("--attacks", default="message_poisoning")
    parser.add_argument("--defenses", default="no_defense,trgc")
    parser.add_argument("--output-root", default="results/runs")
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--max-steps", type=int)
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    try:
        datasets = _split_csv(args.datasets)
        topologies = _split_csv(args.topologies)
        attacks = _split_csv(args.attacks)
        defenses = _split_csv(args.defenses)
        batch_id = args.batch_id or _default_batch_id(args)

        resolver_config = TaskResolverConfig(
            mode=args.task_source_mode,
            datasets=datasets,
            task_limit_per_dataset=args.task_limit_per_dataset,
            manifest_path=args.manifest_path,
        )
        tasks = TaskResolver().resolve(resolver_config)
        total_runs = len(tasks) * len(topologies) * len(attacks) * len(defenses)

        if args.dry_run:
            output = {
                "batch_id": batch_id,
                "dry_run": True,
                "task_count": len(tasks),
                "total_runs": total_runs,
                "datasets": datasets,
                "topologies": topologies,
                "attacks": attacks,
                "defenses": defenses,
            }
            print(json.dumps(output, ensure_ascii=False, indent=2) if args.json else output)
            return 0

        topology_manager = TopologyManager()
        runner = StageBBatchRunner(
            topology_manager=topology_manager,
            protocol_manager=ProtocolManager(topology_manager=topology_manager),
            agent_profiles=load_agent_profiles(),
            prompt_builder=PromptBuilder(),
            safety_verifier=SafetyVerifier(mode="mock"),
            output_root=args.output_root,
        )
        result = runner.run_batch(
            tasks,
            StageBBatchConfig(
                batch_id=batch_id,
                task_source_mode=args.task_source_mode,
                datasets=datasets,
                task_limit_per_dataset=args.task_limit_per_dataset,
                topologies=topologies,
                attacks=attacks,
                defenses=defenses,
                output_root=args.output_root,
                overwrite=args.overwrite,
                max_steps=args.max_steps,
                use_mock_llm=True,
            ),
        )
        output = _summary(result)
        print(json.dumps(output, ensure_ascii=False, indent=2) if args.json else output)
        return 0 if result.failed_runs == 0 else 2
    except Exception as exc:
        if args.json:
            print(json.dumps({"ok": False, "error": type(exc).__name__, "message": str(exc)}))
        else:
            print(f"Stage-B batch failed: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
