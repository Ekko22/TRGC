from lmas_trgc.judging.contracts import build_judge_contract_from_task_packet, determine_metric
from lmas_trgc.tasks.anchors import build_task_packet
from lmas_trgc.tasks.local_synthetic import generate_local_mas_safety_set


def test_build_judge_contract_from_task_packet():
    packet = build_task_packet(generate_local_mas_safety_set(1)[0])
    contract = build_judge_contract_from_task_packet(packet)
    assert contract.metric == "task_success_and_safety"
    assert contract.expected_answer == "safe"


def test_safety_contract_fields_carried():
    packet = build_task_packet(generate_local_mas_safety_set(1)[0])
    contract = build_judge_contract_from_task_packet(packet)
    assert contract.forbidden_actions
    assert contract.forbidden_paths


def test_determine_metric():
    packet = build_task_packet(generate_local_mas_safety_set(1)[0])
    assert determine_metric(packet) == packet.answer_contract["metric"]
