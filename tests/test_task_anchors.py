from lmas_trgc.tasks.anchors import build_task_packet, extract_anchors
from lmas_trgc.tasks.schema import TaskRecord


def test_math_numbers_become_numeric_anchors():
    task = TaskRecord(
        task_id="math_1",
        dataset="gsm8k",
        domain="math_reasoning",
        split="test",
        prompt="Alice has 12 apples and buys 3.5 more boxes.",
        gold_answer="15.5",
    )
    anchors = extract_anchors(task)
    assert any(anchor.anchor_type == "numeric" and anchor.value == "12" for anchor in anchors)
    assert any(anchor.anchor_type == "numeric" and anchor.value == "3.5" for anchor in anchors)


def test_constraints_metadata_extracts_gate_and_forbidden_action():
    task = TaskRecord(
        task_id="constraint_1",
        dataset="constraint_miniset",
        domain="constraints",
        split="test",
        prompt="Decide access.",
        gold_answer="denied",
        metadata={
            "constraints": {
                "forbidden_actions": ["bypass approval"],
                "decisive_gate": "approval_status",
            }
        },
    )
    anchors = extract_anchors(task)
    assert any(anchor.key == "decisive_gate" and anchor.anchor_type == "constraint" for anchor in anchors)
    assert any(anchor.anchor_type == "forbidden_action" for anchor in anchors)


def test_local_mas_safety_metadata_extracts_forbidden_items():
    task = TaskRecord(
        task_id="safety_1",
        dataset="local_mas_safety",
        domain="local_mas_safety",
        split="test",
        prompt="Classify action.",
        gold_answer="unsafe",
        metadata={
            "forbidden_paths": ["private/key"],
            "forbidden_actions": ["upload"],
        },
    )
    anchors = extract_anchors(task)
    assert any(anchor.key.startswith("forbidden_path") for anchor in anchors)
    assert any(anchor.anchor_type == "forbidden_action" for anchor in anchors)


def test_task_packet_contains_contracts():
    task = TaskRecord(
        task_id="packet_1",
        dataset="constraint_miniset",
        domain="constraints",
        split="test",
        prompt="Check constraints.",
        gold_answer="allowed",
        metadata={"violation_types": ["constraint_flip"]},
    )
    packet = build_task_packet(task)
    assert packet.answer_contract["metric"] == "task_success_and_safety"
    assert "violation_types" in packet.safety_contract
    assert "target_slots" in packet.attack_surface


def test_code_prompt_extracts_code_spec_anchor():
    task = TaskRecord(
        task_id="code_1",
        dataset="humaneval",
        domain="code",
        split="test",
        prompt="def add(a, b):\n    return a + b",
        gold_answer="pass",
    )
    anchors = extract_anchors(task)
    assert any(anchor.anchor_type == "code_spec" for anchor in anchors)
