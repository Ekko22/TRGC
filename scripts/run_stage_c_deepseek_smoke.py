#!/usr/bin/env python
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from lmas_trgc.agents.prompt_builder import PromptBuilder
from lmas_trgc.agents.roles import load_agent_profiles
from lmas_trgc.analysis.run_summary import build_run_summary_record
from lmas_trgc.analysis.standard_metrics import build_standard_run_metrics
from lmas_trgc.attacks.manager import AttackManager
from lmas_trgc.core.config import load_dotenv_if_exists
from lmas_trgc.core.ids import make_run_id
from lmas_trgc.defenses.factory import create_defense_adapter
from lmas_trgc.defenses.trgc.safety_verifier import SafetyVerifier
from lmas_trgc.judging.judge import create_judge
from lmas_trgc.llm.factory import (
    build_deepseek_client_from_registry,
    build_safety_verifier_from_registry,
    build_single_model_agent_clients,
    check_deepseek_configuration,
)
from lmas_trgc.llm.registry import build_model_registry
from lmas_trgc.logging.artifact_writer import RunArtifactWriter
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
        raise ValueError(f"DeepSeek smoke only supports synthetic datasets, got: {dataset}")
    if index < 0 or index >= len(tasks):
        raise IndexError(f"task-index {index} out of range for {dataset}; available 0..{len(tasks)-1}")
    return tasks[index]


def _config_status(registry, missing: list[str], sv_mode: str) -> dict:
    m1 = registry.get_task_model("M1")
    sv = registry.get_safety_verifier()
    return {
        "m1_model_name": m1.model_name,
        "m1_base_url_set": bool(m1.base_url),
        "m1_api_key_set": m1.api_key_set,
        "sv_mode": sv_mode,
        "sv_model_name": sv.model_name if sv_mode == "client" else None,
        "sv_base_url_set": bool(sv.base_url) if sv_mode == "client" else None,
        "sv_api_key_set": sv.api_key_set if sv_mode == "client" else None,
        "missing": missing,
        "did_call_real_llm": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Run explicit opt-in DeepSeek single-model Stage-C smoke.")
    parser.add_argument("--confirm-real-llm", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--check-config-only", action="store_true")
    parser.add_argument("--topology", choices=["star", "chain", "graph", "tree"], default="graph")
    parser.add_argument(
        "--attack",
        choices=["none", "message_poisoning", "role_impersonation", "relay_injection"],
        default="message_poisoning",
    )
    parser.add_argument(
        "--defense",
        choices=["no_defense", "simple_content_guardrail", "full_checking_light", "gsafeguard", "trgc"],
        default="trgc",
    )
    parser.add_argument("--dataset", choices=["local_mas_safety", "constraint_miniset"], default="local_mas_safety")
    parser.add_argument("--task-index", type=int, default=0)
    parser.add_argument("--max-steps", type=int, default=2)
    parser.add_argument("--sv-mode", choices=["mock", "client"], default="mock")
    parser.add_argument("--save-artifact", action="store_true")
    parser.add_argument("--output-root", default="results/runs")
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--judge-mode", choices=["rule_based", "mock_protocol"], default="rule_based")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--models-config", default="configs/models.example.yaml")
    parser.add_argument("--require-key", action="store_true", default=True)
    args = parser.parse_args()

    try:
        load_dotenv_if_exists()
        registry = build_model_registry(Path(args.models_config), require_keys=False)
        missing = check_deepseek_configuration(registry, require_sv=args.sv_mode == "client")
        if args.check_config_only:
            status = _config_status(registry, missing, args.sv_mode)
            print(json.dumps(status, ensure_ascii=False, indent=2) if args.json else status)
            return 1 if missing else 0

        task = _task_for(args.dataset, args.task_index)
        run_id = make_run_id(
            stage="stage_c_deepseek_smoke",
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
                "attack": args.attack,
                "defense": args.defense,
                "dataset": args.dataset,
                "max_steps": args.max_steps,
                "sv_mode": args.sv_mode,
                "judge_mode": args.judge_mode,
                "task_agent_model_slot": "M1",
                "task_agent_model_name": registry.get_task_model("M1").model_name,
                "agents": [f"A{idx}" for idx in range(1, 8)],
                "missing_config": missing,
                "did_call_real_llm": False,
                "dry_run": True,
            }
            print(json.dumps(output, ensure_ascii=False, indent=2) if args.json else output)
            return 0

        if not args.confirm_real_llm:
            output = {
                "ok": False,
                "message": "Refusing to call DeepSeek without --confirm-real-llm",
                "did_call_real_llm": False,
            }
            print(json.dumps(output, ensure_ascii=False, indent=2) if args.json else output)
            return 2
        if missing:
            output = {
                "ok": False,
                "message": "DeepSeek configuration is incomplete.",
                "missing": missing,
                "did_call_real_llm": False,
            }
            print(json.dumps(output, ensure_ascii=False, indent=2) if args.json else output)
            return 1

        topology_manager = TopologyManager()
        profiles = load_agent_profiles()
        deepseek_client = build_deepseek_client_from_registry(registry, require_key=args.require_key)
        agent_clients = build_single_model_agent_clients(profiles, deepseek_client)
        verifier = (
            SafetyVerifier(mode="mock")
            if args.sv_mode == "mock"
            else build_safety_verifier_from_registry(registry, require_key=args.require_key, mode="client")
        )
        adapter = create_defense_adapter(args.defense, topology_manager, safety_verifier=verifier)
        task_packet = build_task_packet(task)
        executor = SingleRunExecutor(
            topology_manager=topology_manager,
            protocol_manager=ProtocolManager(topology_manager=topology_manager),
            agent_profiles=profiles,
            defense_adapter=adapter,
            llm_clients_by_agent=agent_clients,
            prompt_builder=PromptBuilder(),
            attack_manager=AttackManager(args.attack),
        )
        result = executor.run(
            task_packet,
            SingleRunConfig(
                run_id=run_id,
                topology=args.topology,
                attack_type=args.attack,
                defense_name=args.defense,
                use_mock_llm=False,
                max_steps=args.max_steps,
            ),
        )
        judge_outcome = create_judge(args.judge_mode).judge(result, task_packet)
        standard_metrics = build_standard_run_metrics(build_run_summary_record(result, task_packet), judge_outcome)
        artifact_dir = None
        if args.save_artifact:
            manifest = RunArtifactWriter(args.output_root, stage_name="stage_c_deepseek", overwrite=args.overwrite).write_run_artifact(
                result,
                task_packet,
                config_snapshot={
                    "stage": "stage_c_deepseek_smoke",
                    "topology": args.topology,
                    "attack": args.attack,
                    "defense": args.defense,
                    "dataset": args.dataset,
                    "task_index": args.task_index,
                    "max_steps": args.max_steps,
                    "sv_mode": args.sv_mode,
                    "judge_mode": args.judge_mode,
                    "task_agent_model_slot": "M1",
                    "task_agent_model_name": registry.get_task_model("M1").model_name,
                },
                judge_outcome=judge_outcome,
                standard_metrics=standard_metrics,
            )
            artifact_dir = manifest.artifact_dir
        output = {
            "run_id": result.run_id,
            "task_id": result.task_id,
            "topology": result.topology,
            "attack": result.attack_type,
            "defense": result.defense_name,
            "sv_mode": args.sv_mode,
            "judge_mode": args.judge_mode,
            "completed": result.completed,
            "total_messages": result.total_messages,
            "attacked_messages": result.attacked_messages,
            "blocked_messages": result.blocked_messages,
            "downweighted_messages": result.downweighted_messages,
            "rerouted_messages": result.rerouted_messages,
            "total_llm_calls": result.total_llm_calls,
            "total_input_tokens": result.total_input_tokens,
            "total_output_tokens": result.total_output_tokens,
            "total_tokens": result.total_tokens,
            "task_success": judge_outcome.task_success,
            "attack_success": judge_outcome.attack_success,
            "safety_violation": judge_outcome.safety_violation,
            "robust_success": judge_outcome.robust_success,
            "artifact_dir": artifact_dir,
            "did_call_real_llm": True,
        }
        print(json.dumps(output, ensure_ascii=False, indent=2) if args.json else output)
        return 0
    except Exception as exc:
        output = {
            "ok": False,
            "error": type(exc).__name__,
            "message": str(exc),
            "model_slot": "M1",
            "did_call_real_llm": bool(args.confirm_real_llm),
        }
        if "registry" in locals():
            slot = registry.get_task_model("M1")
            output.update(
                {
                    "model_name": slot.model_name,
                    "base_url_set": bool(slot.base_url),
                    "api_key_set": slot.api_key_set,
                }
            )
        print(json.dumps(output, ensure_ascii=False, indent=2) if args.json else output, file=sys.stderr if not args.json else sys.stdout)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
