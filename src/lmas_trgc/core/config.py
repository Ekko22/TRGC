from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml


class ConfigError(ValueError):
    """Raised when project configuration cannot be loaded or resolved."""


def load_yaml(path: str | Path) -> dict[str, Any]:
    config_path = Path(path)
    if not config_path.is_absolute():
        config_path = Path.cwd() / config_path
    try:
        with config_path.open("r", encoding="utf-8") as fh:
            data = yaml.safe_load(fh)
    except FileNotFoundError as exc:
        raise ConfigError(f"YAML config not found: {config_path}") from exc
    except yaml.YAMLError as exc:
        raise ConfigError(f"YAML config failed to parse: {config_path}: {exc}") from exc
    if data is None:
        return {}
    if not isinstance(data, dict):
        raise ConfigError(f"YAML config must contain a mapping at top level: {config_path}")
    return data


def load_project_config(config_dir: str | Path) -> dict[str, dict[str, Any]]:
    root = Path(config_dir)
    names = [
        "models.example.yaml",
        "agents.yaml",
        "topologies.yaml",
        "attacks.yaml",
        "defenses.yaml",
        "experiment_main.yaml",
        "experiment_pilot.yaml",
    ]
    return {name: load_yaml(root / name) for name in names}


def resolve_env_value(env_name: str, default: str | None = None, required: bool = False) -> str | None:
    value = os.environ.get(env_name)
    if value:
        return value
    if required and default is None:
        raise ConfigError(f"Required environment variable is missing: {env_name}")
    return default
