import pytest

from lmas_trgc.tasks.public_adapters import (
    convert_aqua_item,
    convert_csqa_item,
    convert_gsm8k_item,
    convert_humaneval_item,
    convert_mbpp_item,
    convert_mmlu_item,
    convert_prontoqa_item,
    convert_public_item,
    convert_svamp_item,
)


def test_convert_gsm8k_extracts_hash_answer():
    task = convert_gsm8k_item({"question": "What is 40 + 2?", "answer": "Reasoning #### 42"}, 0)
    assert task.gold_answer == "42"
    assert task.domain == "math_reasoning"


def test_convert_gsm8k_preserves_integer_trailing_zeroes():
    task = convert_gsm8k_item({"question": "Profit?", "answer": "Reasoning #### 70000"}, 0)
    assert task.gold_answer == "70000"


def test_convert_prontoqa_logic_task_metadata():
    task = convert_prontoqa_item(
        {
            "question": "If A implies B and target is A, is target B?",
            "answer": "true",
            "choices": ["A. true", "B. false"],
            "rule_chain": ["A -> B", "target -> A"],
            "target_property": "B",
            "attackable_link": "A -> B",
            "gold_label": "true",
        },
        0,
    )
    assert task.dataset == "prontoqa"
    assert task.domain == "logic_reasoning"
    assert task.metadata["target_property"] == "B"


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


def test_convert_aqua_extracts_embedded_letter_choices():
    task = convert_aqua_item(
        {
            "question": "Pick the number. A)12 B)24 C)42 D)48 E)49",
            "correct": "C",
        },
        0,
    )
    assert task.gold_answer == "C"
    assert len(task.choices) == 5
    assert task.choices[0] == "A. 12"


def test_convert_aqua_uses_final_complete_choice_sequence():
    task = convert_aqua_item(
        {
            "question": (
                "Vitamin A. If the prompt mentions A before options, choose. "
                "A. 8.5 B. 10.5 C. 12.5 D. 14.5 E. 16.5"
            ),
            "correct": "C",
        },
        0,
    )
    assert task.choices == ["A. 8.5", "B. 10.5", "C. 12.5", "D. 14.5", "E. 16.5"]


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
