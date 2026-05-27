from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml
from dotenv import load_dotenv


class ConfigError(ValueError):
    """Raised when project configuration cannot be loaded or resolved."""


@dataclass(frozen=True)
class ProjectPaths:
    project_root: Path
    config_dir: Path
    data_dir: Path
    results_dir: Path


def find_project_root(start: Path | None = None) -> Path:
    current = (start or Path.cwd()).resolve()
    if current.is_file():
        current = current.parent
    for candidate in [current, *current.parents]:
        if (candidate / "pyproject.toml").exists() and (candidate / "configs").is_dir():
            return candidate
    raise RuntimeError(f"Could not find LMAS-TRGC project root from start path: {current}")


def get_project_paths(start: Path | None = None) -> ProjectPaths:
    root = find_project_root(start)
    return ProjectPaths(
        project_root=root,
        config_dir=root / "configs",
        data_dir=root / "data",
        results_dir=root / "results",
    )


def load_yaml(path: str | Path) -> dict[str, Any]:
    config_path = Path(path)
    if not config_path.is_absolute():
        config_path = Path.cwd() / config_path
    try:
        with config_path.open("r", encoding="utf-8") as fh:
            data = yaml.safe_load(fh)
    except FileNotFoundError as exc:
        raise FileNotFoundError(f"YAML config not found: {config_path}") from exc
    except yaml.YAMLError as exc:
        raise ValueError(f"YAML config failed to parse: {config_path}: {exc}") from exc
    if data is None:
        return {}
    if not isinstance(data, dict):
        raise ValueError(f"YAML config must contain a mapping at top level: {config_path}")
    return data


def load_config_file(config_name: str, config_dir: Path | None = None) -> dict[str, Any]:
    root = config_dir or get_project_paths().config_dir
    return load_yaml(root / config_name)


def load_project_config(config_dir: str | Path) -> dict[str, dict[str, Any]]:
    root = Path(config_dir)
    names = [
        "models.example.yaml",
        "datasets.yaml",
        "agents.yaml",
        "protocols.yaml",
        "topologies.yaml",
        "attacks.yaml",
        "attack_targets.yaml",
        "defenses.yaml",
        "experiment_main.yaml",
        "experiment_pilot.yaml",
    ]
    return {name: load_yaml(root / name) for name in names}


def resolve_env_value(env_name: str | None, default: str | None = None, required: bool = False) -> str | None:
    if not env_name:
        return default
    value = os.environ.get(env_name)
    if value:
        return value
    if required:
        raise RuntimeError(f"Required environment variable is missing: {env_name}")
    return default


def redact_secret(value: str | None) -> str:
    if value is None or value == "":
        return "MISSING"
    return f"SET(length={len(value)})"


def load_dotenv_if_exists(project_root: Path | None = None) -> bool:
    root = project_root or find_project_root()
    dotenv_path = root / ".env"
    if not dotenv_path.exists():
        return False
    load_dotenv(dotenv_path=dotenv_path, override=False)
    return True
