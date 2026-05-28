from lmas_trgc.tasks.local_synthetic import (
    generate_all_synthetic_tasks,
    generate_constraint_miniset,
    generate_local_mas_safety_set,
)
from lmas_trgc.tasks.schema import TaskRecord


def test_generate_constraint_miniset_count_and_validation():
    tasks = generate_constraint_miniset(16)
    assert len(tasks) == 16
    assert all(isinstance(task, TaskRecord) for task in tasks)
    assert len({task.prompt for task in tasks}) == 16
    constraint_counts = {kind: 0 for kind in [
        "access_control",
        "approval_workflow",
        "qualification_check",
        "scheduling_conflict",
        "order_dependency",
    ]}
    for task in tasks:
        constraint_counts[task.metadata["constraint_type"]] += 1
        for key in [
            "policy_rules",
            "case_facts",
            "decisive_gate",
            "gold_gate_value",
            "attack_flip_value",
            "allowed_actions",
            "forbidden_actions",
            "violation_types",
            "task_anchors",
            "target_slots",
            "attack_surfaces",
            "judge_type",
            "answer_format",
        ]:
            assert key in task.metadata
        assert set(task.metadata["attack_surfaces"]) == {
            "message_poisoning",
            "role_impersonation",
            "relay_injection",
        }
    assert constraint_counts == {
        "access_control": 4,
        "approval_workflow": 3,
        "qualification_check": 3,
        "scheduling_conflict": 3,
        "order_dependency": 3,
    }


def test_generate_local_mas_safety_count_balance_and_validation():
    tasks = generate_local_mas_safety_set(16)
    assert len(tasks) == 16
    assert len({task.prompt for task in tasks}) == 16
    answers = [task.gold_answer for task in tasks]
    assert answers.count("safe") == 8
    assert answers.count("unsafe") == 8
    scenario_counts: dict[str, int] = {}
    violation_types: set[str] = set()
    for task in tasks:
        scenario_counts[task.metadata["scenario_type"]] = scenario_counts.get(task.metadata["scenario_type"], 0) + 1
        violation_types.update(task.metadata["violation_types"])
        for key in [
            "allowed_paths",
            "forbidden_paths",
            "allowed_actions",
            "forbidden_actions",
            "required_review_steps",
            "unsafe_target_action",
            "violation_types",
            "task_anchors",
            "target_slots",
            "attack_surfaces",
            "judge_type",
            "answer_format",
        ]:
            assert key in task.metadata
        assert set(task.metadata["attack_surfaces"]) == {
            "message_poisoning",
            "role_impersonation",
            "relay_injection",
        }
    assert scenario_counts == {
        "file_path_control": 4,
        "credential_access": 4,
        "network_exfiltration": 4,
        "review_bypass": 4,
    }
    assert {
        "forbidden_path_access",
        "credential_access",
        "unauthorized_upload",
        "deletion_without_approval",
        "review_bypass",
        "unsupported_authority_claim",
    }.issubset(violation_types)
    assert all(isinstance(task, TaskRecord) for task in tasks)


def test_synthetic_task_ids_are_stable():
    first = [task.task_id for task in generate_constraint_miniset(4)]
    second = [task.task_id for task in generate_constraint_miniset(4)]
    assert first == second


def test_generate_all_synthetic_tasks_keys():
    tasks = generate_all_synthetic_tasks()
    assert set(tasks) == {"constraint_miniset", "local_mas_safety"}
