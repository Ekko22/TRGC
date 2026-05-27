from __future__ import annotations

from lmas_trgc.core.config import load_yaml


def summarize_stage_config(path: str) -> dict:
    config = load_yaml(path)
    return {
        "stage": config.get("stage"),
        "topologies": len(config.get("topologies", [])),
        "attacks": len(config.get("attacks", [])),
        "defenses": len(config.get("defenses", [])),
    }
