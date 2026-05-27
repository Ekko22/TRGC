from lmas_trgc.attacks.manager import AttackManager
from lmas_trgc.communication.message import AgentMessage
from lmas_trgc.tasks.anchors import build_task_packet
from lmas_trgc.tasks.local_synthetic import generate_local_mas_safety_set


def _packet():
    return build_task_packet(generate_local_mas_safety_set(1)[0])


def _message(sender="A3", receiver="A7"):
    return AgentMessage(
        message_id="msg_attack",
        parent_message_id="parent",
        round_id=1,
        sender=sender,
        receiver=receiver,
        sender_role="WorkerA",
        receiver_role="FinalizerExecutor",
        message_type="INTERMEDIATE_RESULT",
        content="Mock result.",
        reasoning_summary=None,
        confidence=None,
        task_id="task_attack",
    )


def _route_meta(sender="A3", receiver="A7", topology="graph"):
    return {
        "topology": topology,
        "sender": sender,
        "receiver": receiver,
        "edge": f"{sender}->{receiver}",
    }


def test_none_attack_does_not_attack():
    message = _message()
    attacked, result = AttackManager("none").apply_attack_if_needed(message, _route_meta(), _packet())
    assert attacked is message
    assert result is None


def test_message_poisoning_attacks_high_value_edge():
    message = _message()
    attacked, result = AttackManager("message_poisoning").apply_attack_if_needed(message, _route_meta(), _packet())
    assert result is not None and result.attacked is True
    assert "Injected communication update" in attacked.content
    assert result.changed_fields
    assert result.original_content_hash != result.attacked_content_hash
    assert message.content == "Mock result."


def test_role_impersonation_sets_declared_authority():
    message = _message(receiver="A1")
    attacked, result = AttackManager("role_impersonation").apply_attack_if_needed(
        message,
        _route_meta(receiver="A1", topology="star"),
        _packet(),
    )
    assert result is not None and result.attacked is True
    assert attacked.declared_authority in {"Planner", "DomainReviewer"}
    assert message.declared_authority is None


def test_relay_injection_sets_forwarded_flag():
    message = _message(sender="A3", receiver="A7")
    attacked, result = AttackManager("relay_injection").apply_attack_if_needed(message, _route_meta(), _packet())
    assert result is not None and result.attacked is True
    assert attacked.is_forwarded is True
    assert message.is_forwarded is False
