#!/usr/bin/env python
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from lmas_trgc.core.config import find_project_root, load_dotenv_if_exists
from lmas_trgc.llm.client import OpenAICompatibleClient
from lmas_trgc.llm.registry import ModelRegistry, ModelSlotConfig, build_model_registry


def _slot_rows(registry: ModelRegistry, include_sv: bool) -> list[ModelSlotConfig]:
    rows = [registry.task_models[slot] for slot in registry.list_task_model_slots()]
    if include_sv:
        rows.append(registry.get_safety_verifier())
    return rows


def _check_endpoint(slot: ModelSlotConfig, timeout: float) -> tuple[bool, list[str], str | None]:
    if not slot.api_key_set or not slot.base_url:
        return False, [], "not_checked_missing_key_or_base_url"
    api_key = os.environ.get(slot.api_key_env)
    client = OpenAICompatibleClient(
        model_name=slot.model_name or "unknown",
        base_url=slot.base_url,
        api_key=api_key,
        timeout=timeout,
        max_retries=0,
    )
    try:
        return True, client.list_models(), None
    except Exception as exc:
        return False, [], type(exc).__name__


def _build_results(args: argparse.Namespace) -> list[dict]:
    project_root = find_project_root()
    load_dotenv_if_exists(project_root)
    registry = build_model_registry(Path(args.models_config), require_keys=args.require_keys)
    results = []
    for slot in _slot_rows(registry, include_sv=args.include_sv):
        endpoint_checked = bool(args.check_models_endpoint and slot.api_key_set and slot.base_url)
        reachable = False
        models: list[str] = []
        error = None
        if args.check_models_endpoint:
            reachable, models, error = _check_endpoint(slot, args.timeout)
            endpoint_checked = error != "not_checked_missing_key_or_base_url"
        results.append(
            {
                "slot": slot.slot_id,
                "model_name": slot.model_name,
                "provider": slot.provider,
                "base_url_set": bool(slot.base_url),
                "api_key_set": slot.api_key_set,
                "is_task_agent": slot.is_task_agent,
                "endpoint_checked": endpoint_checked,
                "endpoint_reachable": reachable,
                "models": models,
                "error": error,
            }
        )
    return results


def _print_markdown(results: list[dict]) -> None:
    print("| slot | model_name | provider | base_url_set | api_key_set | is_task_agent | endpoint_checked | endpoint_reachable | models | error |")
    print("|---|---|---|---|---|---|---|---|---|---|")
    for row in results:
        models = ", ".join(row["models"]) if row["models"] else ""
        print(
            "| {slot} | {model_name} | {provider} | {base_url_set} | {api_key_set} | "
            "{is_task_agent} | {endpoint_checked} | {endpoint_reachable} | {models} | {error} |".format(
                **{**row, "models": models, "error": row["error"] or ""}
            )
        )


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit LMAS-TRGC model configuration and optional /models endpoints.")
    parser.add_argument("--models-config", default="configs/models.example.yaml")
    parser.add_argument("--check-models-endpoint", action="store_true")
    parser.add_argument("--require-keys", action="store_true")
    parser.add_argument("--include-sv", dest="include_sv", action="store_true", default=True)
    parser.add_argument("--no-include-sv", dest="include_sv", action="store_false")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--timeout", type=float, default=5.0)
    args = parser.parse_args()

    try:
        results = _build_results(args)
    except Exception as exc:
        if args.json:
            print(json.dumps({"ok": False, "error": type(exc).__name__, "message": str(exc)}, indent=2))
        else:
            print(f"Configuration check failed: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1

    if args.json:
        print(json.dumps({"ok": True, "results": results}, indent=2))
    else:
        _print_markdown(results)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
