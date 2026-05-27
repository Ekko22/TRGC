import pytest

from lmas_trgc.tasks.public_adapters import (
    convert_csqa_item,
    convert_gsm8k_item,
    convert_humaneval_item,
    convert_mbpp_item,
    convert_mmlu_item,
    convert_public_item,
    convert_svamp_item,
)


def test_convert_gsm8k_extracts_hash_answer():
    task = convert_gsm8k_item({"question": "What is 40 + 2?", "answer": "Reasoning #### 42"}, 0)
    assert task.gold_answer == "42"
    assert task.domain == "math_reasoning"


def test_convert_mmlu_int_answer_to_letter():
    task = convert_mmlu_item(
        {"question": "Pick one.", "choices": ["a", "b", "c", "d"], "answer": 1, "subject": "demo"},
        0,
    )
    assert task.gold_answer == "B"
    assert len(task.choices) == 4


def test_convert_csqa_hf_choices_and_answer_key():
    task = convert_csqa_item(
        {
            "question": "Where do people read?",
            "choices": {"label": ["A"], "text": ["library"]},
            "answerKey": "A",
        },
        0,
    )
    assert task.choices == ["A. library"]
    assert task.gold_answer == "A"


def test_convert_svamp_combines_body_and_question():
    task = convert_svamp_item({"Body": "A has 2.", "Question": "Adds 3?", "Answer": 5}, 0)
    assert "A has 2." in task.prompt
    assert "Adds 3?" in task.prompt
    assert task.gold_answer == "5"


def test_convert_humaneval_metadata():
    task = convert_humaneval_item(
        {
            "task_id": "HumanEval/1",
            "prompt": "def add(a, b):",
            "canonical_solution": " return a + b",
            "entry_point": "add",
            "test": "assert add(1, 2) == 3",
        },
        0,
    )
    assert task.domain == "code"
    assert task.metadata["entry_point"] == "add"


def test_convert_mbpp_code_task():
    task = convert_mbpp_item(
        {
            "task_id": 1,
            "text": "Write a function.",
            "code": "def f(): return 1",
            "test_list": ["assert f() == 1"],
        },
        0,
    )
    assert task.domain == "code"
    assert task.gold_answer == "def f(): return 1"


def test_convert_public_item_unknown_dataset_raises():
    with pytest.raises(ValueError):
        convert_public_item("bad", {"question": "x"}, 0, "test")
