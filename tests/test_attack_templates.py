from lmas_trgc.attacks.templates import (
    append_attack_payload,
    build_message_poisoning_payload,
    build_relay_injection_payload,
    build_role_impersonation_payload,
)
from lmas_trgc.tasks.anchors import build_task_packet
from lmas_trgc.tasks.local_synthetic import generate_constraint_miniset


def _packet():
    return build_task_packet(generate_constraint_miniset(1)[0])


def test_message_poisoning_payload_has_update_semantics():
    payload = build_message_poisoning_payload(_packet(), "numeric")
    assert "Updated" in payload or "corrected" in payload


def test_role_impersonation_payload_has_planner_semantics():
    payload = build_role_impersonation_payload(_packet(), "permission")
    assert "Planner-approved" in payload or "planner" in payload.lower()


def test_relay_payload_has_forwarded_semantics():
    payload = build_relay_injection_payload(_packet(), "logic_rule")
    assert "Forwarded" in payload or "upstream" in payload


def test_append_attack_payload_preserves_original_and_marker():
    content = append_attack_payload("original", "payload")
    assert "original" in content
    assert "Injected communication update" in content


def test_payloads_do_not_include_shell_commands():
    payloads = [
        build_message_poisoning_payload(_packet(), None),
        build_role_impersonation_payload(_packet(), None),
        build_relay_injection_payload(_packet(), None),
    ]
    forbidden = ["rm -rf", "curl", "wget", "scp"]
    for payload in payloads:
        assert not any(term in payload for term in forbidden)
