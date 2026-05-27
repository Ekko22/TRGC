import pytest
from pydantic import ValidationError

from lmas_trgc.communication.message import AgentMessage


def _message(**overrides):
    data = {
        "message_id": "msg_1",
        "parent_message_id": None,
        "round_id": 0,
        "sender": "A1",
        "receiver": "A2",
        "sender_role": "Planner",
        "receiver_role": "Worker",
        "message_type": "task_assignment",
        "content": "Solve this task.",
        "reasoning_summary": None,
        "confidence": 0.8,
        "task_id": "task_1",
    }
    data.update(overrides)
    return AgentMessage(**data)


def test_agent_message_constructs():
    message = _message()
    assert message.sender == "A1"
    assert message.confidence == 0.8


def test_confidence_out_of_range_fails():
    with pytest.raises(ValidationError):
        _message(confidence=1.5)


def test_empty_sender_fails():
    with pytest.raises(ValidationError):
        _message(sender="")
