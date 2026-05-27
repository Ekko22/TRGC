import pytest
from pydantic import ValidationError

from lmas_trgc.tasks.schema import TaskAnchor, TaskPacket, TaskRecord


def _task(**overrides):
    data = {
        "task_id": "task_1",
        "dataset": "gsm8k",
        "domain": "math_reasoning",
        "split": "test",
        "prompt": "What is 2 + 2?",
        "gold_answer": "4",
    }
    data.update(overrides)
    return TaskRecord(**data)


def test_task_record_constructs():
    task = _task()
    assert task.task_id == "task_1"
    assert task.gold_answer == "4"


def test_empty_prompt_fails():
    with pytest.raises(ValidationError):
        _task(prompt="")


def test_invalid_domain_fails():
    with pytest.raises(ValidationError):
        _task(domain="bad_domain")


def test_invalid_dataset_fails():
    with pytest.raises(ValidationError):
        _task(dataset="bad_dataset")


def test_task_packet_constructs():
    task = _task()
    packet = TaskPacket(
        task=task,
        anchors=[],
        answer_contract={"metric": "exact_match"},
        safety_contract={"violation_types": []},
        attack_surface={"target_slots": ["content"]},
    )
    assert packet.task.task_id == task.task_id


def test_anchor_confidence_range():
    with pytest.raises(ValidationError):
        TaskAnchor(
            anchor_id="a1",
            task_id="task_1",
            key="k",
            value="v",
            anchor_type="numeric",
            confidence=1.5,
        )
