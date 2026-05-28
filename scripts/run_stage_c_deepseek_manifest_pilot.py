#!/usr/bin/env python
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from lmas_trgc.agents.prompt_builder import PromptBuilder
from lmas_trgc.agents.roles import load_agent_profiles
from lmas_trgc.core.config import load_dotenv_if_exists
from lmas_trgc.core.ids import stable_hash
from lmas_trgc.llm.factory import check_deepseek_configuration
from lmas_trgc.llm.registry import build_model_registry
from lmas_trgc.runners.manifest_pilot import (
    ManifestPilotTaskSelectionConfig,
    StageCDeepSeekManifestPilotConfig,
    StageCDeepSeekManifestPilotRunner,
    resolve_manifest_task_records,
)
from lmas_trgc.runners.protocol import ProtocolManager
from lmas_trgc.topology.manager import TopologyManager


def _parse_csv(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


def _default_batch_id(args: argparse.Namespace) -> str:
    return "stage_c_manifest_" + stable_hash(
        args.manifest_path,
        args.tasks_per_dataset,
        args.datasets,
        args.topologies,
        args.attacks,
        args.defenses,
        args.max_steps,
        length=12,
    )


def _summary_from_config(
    args: argparse.Namespace,
    registry,
    selected_tasks,
    missing: list[str],
    sv_missing: list[str],
    *,
    did_call_real_llm: bool = False,
) -> dict:
    selected_datasets = []
    for task in selected_tasks:
        if task.dataset not in selected_datasets:
            selected_datasets.append(task.dataset)
    total_runs = len(selected_tasks) * len(_parse_csv(args.topologies)) * len(_parse_csv(args.attacks)) * len(_parse_csv(args.defenses))
    return {
        "batch_id": args.batch_id,
        "manifest_path": args.manifest_path,
        "selected_tasks": len(selected_tasks),
        "selected_datasets": selected_datasets,
        "topologies": _parse_csv(args.topologies),
        "attacks": _parse_csv(args.attacks),
        "defenses": _parse_csv(args.defenses),
        "total_runs": total_runs,
        "max_steps": args.max_steps,
        "sv_mode": args.sv_mode,
        "judge_mode": args.judge_mode,
        "max_workers": args.max_workers,
        "show_progress": not args.no_progress,
        "fail_fast": args.fail_fast,
        "task_agent_model_slot": "M1",
        "task_agent_model_name": registry.get_task_model("M1").model_name,
        "agents": [f"A{idx}" for idx in range(1, 8)],
        "missing_config": missing,
        "sv_missing_config": sv_missing,
        "did_call_real_llm": did_call_real_llm,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Run explicit opt-in DeepSeek Stage-C manifest pilot.")
    parser.add_argument("--confirm-real-llm", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--check-config-only", action="store_true")
    parser.add_argument("--batch-id")
    parser.add_argument("--manifest-path", default="data/manifests/main_manifest.json")
    parser.add_argument("--tasks-per-dataset", type=int, default=1)
    parser.add_argument("--datasets", default="")
    parser.add_argument("--topologies", default="graph")
    parser.add_argument("--attacks", default="message_poisoning")
    parser.add_argument("--defenses", default="no_defense,trgc")
    parser.add_argument("--max-steps", type=int, default=3)
    parser.add_argument("--sv-mode", choices=["mock", "client"], default="client")
    parser.add_argument("--allow-sv-mock-fallback", action="store_true")
    parser.add_argument("--judge-mode", choices=["rule_based", "mock_protocol"], default="rule_based")
    parser.add_argument("--output-root", default="results/runs")
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--max-workers", type=int, default=2)
    parser.add_argument("--no-progress", action="store_true")
    parser.add_argument("--fail-fast", action="store_true")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--models-config", default="configs/models.example.yaml")
    args = parser.parse_args()
    if not args.batch_id:
        args.batch_id = _default_batch_id(args)

    try:
        if args.max_workers < 1:
            raise ValueError("--max-workers must be >= 1")
        high_workers_warning = "High max-workers may trigger API rate limits."
        if args.max_workers > 4 and (args.dry_run or args.check_config_only or not args.confirm_real_llm):
            print(high_workers_warning, file=sys.stderr)
        load_dotenv_if_exists()
        registry = build_model_registry(Path(args.models_config), require_keys=False)
        missing = check_deepseek_configuration(registry, require_sv=False)
        sv_missing = [
            item for item in check_deepseek_configuration(registry, require_sv=True)
            if item.startswith("SV ")
        ] if args.sv_mode == "client" else []
        selected_tasks = resolve_manifest_task_records(
            ManifestPilotTaskSelectionConfig(
                manifest_path=args.manifest_path,
                tasks_per_dataset=args.tasks_per_dataset,
                datasets=_parse_csv(args.datasets),
            )
        )

        if args.check_config_only:
            output = _summary_from_config(args, registry, selected_tasks, missing, sv_missing)
            output["ok"] = not missing and (args.sv_mode != "client" or not sv_missing or args.allow_sv_mock_fallback)
            print(json.dumps(output, ensure_ascii=False, indent=2) if args.json else output)
            return 0 if output["ok"] else 1

        if args.dry_run:
            output = _summary_from_config(args, registry, selected_tasks, missing, sv_missing)
            output["dry_run"] = True
            print(json.dumps(output, ensure_ascii=False, indent=2) if args.json else output)
            return 0

        if not args.confirm_real_llm:
            output = {
                "ok": False,
                "message": "Refusing to run real DeepSeek manifest pilot without --confirm-real-llm",
                "did_call_real_llm": False,
                "max_workers": args.max_workers,
                "show_progress": not args.no_progress,
            }
            print(json.dumps(output, ensure_ascii=False, indent=2) if args.json else output)
            return 2

        config = StageCDeepSeekManifestPilotConfig(
            batch_id=args.batch_id,
            manifest_path=args.manifest_path,
            tasks_per_dataset=args.tasks_per_dataset,
            datasets=_parse_csv(args.datasets),
            topologies=_parse_csv(args.topologies),
            attacks=_parse_csv(args.attacks),
            defenses=_parse_csv(args.defenses),
            max_steps=args.max_steps,
            sv_mode=args.sv_mode,
            allow_sv_mock_fallback=args.allow_sv_mock_fallback,
            judge_mode=args.judge_mode,
            output_root=args.output_root,
            overwrite=args.overwrite,
            confirm_real_llm=args.confirm_real_llm,
            max_workers=args.max_workers,
            show_progress=not args.no_progress,
            fail_fast=args.fail_fast,
        )
        topology_manager = TopologyManager()
        runner = StageCDeepSeekManifestPilotRunner(
            topology_manager=topology_manager,
            protocol_manager=ProtocolManager(topology_manager=topology_manager),
            agent_profiles=load_agent_profiles(),
            prompt_builder=PromptBuilder(),
            model_registry=registry,
            output_root=args.output_root,
        )
        result = runner.run_pilot(config)
        output = result.model_dump(mode="json")
        output["did_call_real_llm"] = True
        output["max_workers"] = args.max_workers
        output["show_progress"] = not args.no_progress
        print(json.dumps(output, ensure_ascii=False, indent=2) if args.json else output)
        return 0 if result.completed else 2
    except Exception as exc:
        output = {
            "ok": False,
            "error": type(exc).__name__,
            "message": str(exc),
            "model_slot": "M1",
            "did_call_real_llm": bool(args.confirm_real_llm and not args.dry_run and not args.check_config_only),
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
        print(json.dumps(output, ensure_ascii=False, indent=2) if args.json else output)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
