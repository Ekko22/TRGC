from __future__ import annotations


def describe_single_run(config: dict) -> dict:
    return {"stage": config.get("stage", "unknown"), "status": "described"}
