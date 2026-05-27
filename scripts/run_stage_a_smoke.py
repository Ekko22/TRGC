#!/usr/bin/env python
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from lmas_trgc.agents.prompt_builder import PromptBuilder
from lmas_trgc.agents.roles import load_agent_profiles
from lmas_trgc.core.ids import make_run_id
from lmas_trgc.defenses.factory import create_defense_adapter
from lmas_trgc.defenses.trgc.safety_verifier import SafetyVerifier
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
        raise ValueError(f"Stage-A smoke only supports synthetic datasets, got: {dataset}")
    if index < 0 or index >= len(tasks):
        raise IndexError(f"task-index {index} out of range for {dataset}; available 0..{len(tasks)-1}")
    return tasks[index]


def _summary(result) -> dict:
    return {
        "run_id": result.run_id,
        "task_id": result.task_id,
        "topology": result.topology,
        "defense": result.defense_name,
        "total_messages": result.total_messages,
        "delivered_messages": result.delivered_messages,
        "blocked_messages": result.blocked_messages,
        "downweighted_messages": result.downweighted_messages,
        "rerouted_messages": result.rerouted_messages,
        "completed": result.completed,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Run a mock-only Stage-A LMAS-TRGC smoke execution.")
    parser.add_argument("--config", default="configs/experiment_pilot.yaml")
    parser.add_argument("--topology", choices=["star", "chain", "graph", "tree"], default="star")
    parser.add_argument("--defense", default="trgc")
    parser.add_argument("--dataset", choices=["local_mas_safety", "constraint_miniset"], default="local_mas_safety")
    parser.add_argument("--task-index", type=int, default=0)
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--max-steps", type=int)
    args = parser.parse_args()
    try:
        task = _task_for(args.dataset, args.task_index)
        run_id = make_run_id(
            stage="stage_a_smoke",
            topology=args.topology,
            attack="none",
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
                "dataset": args.dataset,
                "dry_run": True,
            }
            print(json.dumps(output, indent=2) if args.json else output)
            return 0

        task_packet = build_task_packet(task)
        topology_manager = TopologyManager()
        protocol_manager = ProtocolManager(topology_manager=topology_manager)
        agent_profiles = load_agent_profiles()
        clients = {
            agent_id: MockLLMClient(model_name=f"mock-{agent_id}")
            for agent_id in agent_profiles
        }
        safety_verifier = SafetyVerifier(mode="mock")
        defense_adapter = create_defense_adapter(
            args.defense,
            topology_manager=topology_manager,
            safety_verifier=safety_verifier,
        )
        executor = SingleRunExecutor(
            topology_manager=topology_manager,
            protocol_manager=protocol_manager,
            agent_profiles=agent_profiles,
            defense_adapter=defense_adapter,
            llm_clients_by_agent=clients,
            prompt_builder=PromptBuilder(),
        )
        result = executor.run(
            task_packet,
            SingleRunConfig(
                run_id=run_id,
                topology=args.topology,
                attack_type="none",
                defense_name=args.defense,
                use_mock_llm=True,
                max_steps=args.max_steps,
            ),
        )
        summary = _summary(result)
        print(json.dumps(summary, indent=2) if args.json else summary)
        return 0
    except Exception as exc:
        if args.json:
            print(json.dumps({"ok": False, "error": type(exc).__name__, "message": str(exc)}))
        else:
            print(f"Stage-A smoke failed: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
