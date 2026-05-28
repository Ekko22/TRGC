from __future__ import annotations

import re

from lmas_trgc.core.ids import stable_hash
from lmas_trgc.tasks.schema import TaskAnchor, TaskPacket, TaskRecord

ANCHOR_DATASETS = [
    "GSM8K",
    "ProntoQA",
    "MMLU",
    "CSQA",
    "SVAMP",
    "MultiArith",
    "AQuA",
    "HumanEval",
    "MBPP",
    "Constraint MiniSet",
    "Local-MAS Safety Set",
]


def _anchor(task: TaskRecord, key: str, value: str, anchor_type: str, source: str = "auto") -> TaskAnchor:
    anchor_id = "anc_" + stable_hash(task.task_id, key, value, anchor_type, length=16)
    return TaskAnchor(
        anchor_id=anchor_id,
        task_id=task.task_id,
        key=key,
        value=str(value),
        anchor_type=anchor_type,
        source=source,
    )


def _expected_answer_anchor(task: TaskRecord) -> list[TaskAnchor]:
    if task.gold_answer is None:
        return []
    return [_anchor(task, "gold_answer", task.gold_answer, "expected_answer")]


def extract_math_anchors(task: TaskRecord) -> list[TaskAnchor]:
    anchors = [
        _anchor(task, f"number_{idx}", match.group(0), "numeric")
        for idx, match in enumerate(re.finditer(r"-?\d+(?:\.\d+)?", task.prompt), start=1)
    ]
    return anchors + _expected_answer_anchor(task)


def extract_logic_anchors(task: TaskRecord) -> list[TaskAnchor]:
    parts = [part.strip() for part in re.split(r"[.;\n]+", task.prompt) if part.strip()]
    anchors = [_anchor(task, f"rule_{idx}", part, "logic_rule") for idx, part in enumerate(parts, start=1)]
    return anchors + _expected_answer_anchor(task)


def extract_choice_anchors(task: TaskRecord) -> list[TaskAnchor]:
    anchors = [_anchor(task, f"choice_{idx}", choice, "entity") for idx, choice in enumerate(task.choices, start=1)]
    return anchors + _expected_answer_anchor(task)


def extract_code_anchors(task: TaskRecord) -> list[TaskAnchor]:
    anchors: list[TaskAnchor] = []
    for term in ["def ", "return", "assert"]:
        if term in task.prompt:
            anchors.append(_anchor(task, f"code_contains_{term.strip()}", term.strip(), "code_spec"))
    entry_point = task.metadata.get("entry_point")
    if entry_point:
        anchors.append(_anchor(task, "entry_point", str(entry_point), "code_spec"))
    return anchors + _expected_answer_anchor(task)


def extract_constraint_anchors(task: TaskRecord) -> list[TaskAnchor]:
    constraints = task.metadata.get("constraints", {})
    anchors: list[TaskAnchor] = []
    for idx, action in enumerate(constraints.get("allowed_actions", []), start=1):
        anchors.append(_anchor(task, f"allowed_action_{idx}", str(action), "allowed_action"))
    for idx, action in enumerate(constraints.get("forbidden_actions", []), start=1):
        anchors.append(_anchor(task, f"forbidden_action_{idx}", str(action), "forbidden_action"))
    for idx, permission in enumerate(constraints.get("required_permissions", []), start=1):
        anchors.append(_anchor(task, f"required_permission_{idx}", str(permission), "permission"))
    decisive_gate = constraints.get("decisive_gate") or task.metadata.get("decisive_gate")
    if decisive_gate:
        anchors.append(_anchor(task, "decisive_gate", str(decisive_gate), "constraint"))
    return anchors + _expected_answer_anchor(task)


def extract_local_mas_safety_anchors(task: TaskRecord) -> list[TaskAnchor]:
    anchors: list[TaskAnchor] = []
    for idx, path in enumerate(task.metadata.get("allowed_paths", []), start=1):
        anchors.append(_anchor(task, f"allowed_path_{idx}", str(path), "safety_requirement"))
    for idx, path in enumerate(task.metadata.get("forbidden_paths", []), start=1):
        anchors.append(_anchor(task, f"forbidden_path_{idx}", str(path), "safety_requirement"))
    for idx, action in enumerate(task.metadata.get("allowed_actions", []), start=1):
        anchors.append(_anchor(task, f"allowed_action_{idx}", str(action), "allowed_action"))
    for idx, action in enumerate(task.metadata.get("forbidden_actions", []), start=1):
        anchors.append(_anchor(task, f"forbidden_action_{idx}", str(action), "forbidden_action"))
    for idx, step in enumerate(task.metadata.get("required_review_steps", []), start=1):
        anchors.append(_anchor(task, f"required_review_step_{idx}", str(step), "safety_requirement"))
    unsafe_action = task.metadata.get("unsafe_target_action")
    if unsafe_action:
        anchors.append(_anchor(task, "unsafe_target_action", str(unsafe_action), "forbidden_action"))
    return anchors + _expected_answer_anchor(task)


def extract_anchors(task: TaskRecord) -> list[TaskAnchor]:
    if task.domain == "math_reasoning":
        return extract_math_anchors(task)
    if task.domain == "logic_reasoning":
        return extract_logic_anchors(task)
    if task.domain in {"knowledge_reasoning", "commonsense_reasoning"}:
        return extract_choice_anchors(task)
    if task.domain == "code":
        return extract_code_anchors(task)
    if task.domain == "constraints":
        return extract_constraint_anchors(task)
    if task.domain == "local_mas_safety":
        return extract_local_mas_safety_anchors(task)
    return _expected_answer_anchor(task)


def build_answer_contract(task: TaskRecord) -> dict:
    metric_by_dataset = {
        "gsm8k": "exact_match",
        "svamp": "exact_match",
        "multiarith": "exact_match",
        "mmlu": "accuracy",
        "csqa": "accuracy",
        "aqua": "accuracy",
        "humaneval": "pass_at_1_or_review_accuracy",
        "mbpp": "pass_at_1_or_review_accuracy",
        "constraint_miniset": "task_success_and_safety",
        "local_mas_safety": "task_success_and_safety",
    }
    metric = metric_by_dataset[task.dataset]
    return {
        "metric": metric,
        "expected_answer": task.gold_answer,
        "normalization": "lower_strip" if task.domain != "code" else "code_review_contract",
        "exact_match_required": metric == "exact_match",
    }


def build_safety_contract(task: TaskRecord) -> dict:
    constraints = task.metadata.get("constraints", {})
    forbidden_actions = list(constraints.get("forbidden_actions", []))
    forbidden_actions.extend(task.metadata.get("forbidden_actions", []))
    return {
        "violation_types": list(task.metadata.get("violation_types", [])),
        "forbidden_actions": forbidden_actions,
        "forbidden_paths": list(task.metadata.get("forbidden_paths", [])),
        "requires_review": bool(task.metadata.get("required_review_steps")),
    }


def build_attack_surface(task: TaskRecord, anchors: list[TaskAnchor]) -> dict:
    attack_types: set[str] = set()
    critical_anchors: list[str] = []
    for anchor in anchors:
        if anchor.anchor_type == "numeric":
            attack_types.add("message_poisoning")
        if anchor.anchor_type in {"permission", "forbidden_action", "safety_requirement"}:
            attack_types.update({"role_impersonation", "relay_injection", "message_poisoning"})
            critical_anchors.append(anchor.anchor_id)
        if anchor.anchor_type == "code_spec":
            attack_types.update({"message_poisoning", "relay_injection"})
        if anchor.anchor_type == "logic_rule":
            attack_types.add("message_poisoning")
    target_slots = ["content"]
    if any(anchor.anchor_type in {"permission", "forbidden_action", "safety_requirement"} for anchor in anchors):
        target_slots.extend(["declared_authority", "relay_content"])
    return {
        "target_slots": target_slots,
        "likely_attack_types": sorted(attack_types),
        "critical_anchors": critical_anchors,
    }


def build_task_packet(task: TaskRecord) -> TaskPacket:
    anchors = extract_anchors(task)
    return TaskPacket(
        task=task,
        anchors=anchors,
        answer_contract=build_answer_contract(task),
        safety_contract=build_safety_contract(task),
        attack_surface=build_attack_surface(task, anchors),
    )
