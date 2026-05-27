from __future__ import annotations

import hashlib
import json
from typing import Any


def stable_hash(*parts: Any, length: int = 16) -> str:
    """Return a deterministic sha256-based hash for JSON-serializable inputs."""
    payload = json.dumps(parts, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:length]


def make_run_id(*, stage: str, topology: str, attack: str, defense: str, seed: int, task_id: str) -> str:
    return "run_" + stable_hash(stage, topology, attack, defense, seed, task_id, length=20)


def make_message_id(*, task_id: str, round_id: int, sender: str, receiver: str, content: str) -> str:
    return "msg_" + stable_hash(task_id, round_id, sender, receiver, content, length=20)


def make_delivery_id(*, message_id: str, topology: str, sender: str, receiver: str, round_id: int) -> str:
    return "del_" + stable_hash(message_id, topology, sender, receiver, round_id, length=20)
