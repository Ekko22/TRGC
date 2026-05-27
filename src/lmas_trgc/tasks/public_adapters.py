from __future__ import annotations

from collections.abc import Callable

from lmas_trgc.tasks.normalizers import (
    compact_metadata,
    make_public_task_id,
    normalize_answer,
    normalize_choices,
    normalize_text,
)
from lmas_trgc.tasks.schema import TaskRecord


def _require_prompt(dataset: str, index: int, prompt: str) -> str:
    if not prompt:
        raise ValueError(f"{dataset} index {index}: missing prompt/question field")
    return prompt


def _record(
    *,
    dataset: str,
    domain: str,
    index: int,
    split: str,
    prompt: str,
    gold_answer: object,
    choices: list[str] | None = None,
    metadata: dict | None = None,
) -> TaskRecord:
    return TaskRecord(
        task_id=make_public_task_id(dataset, split, index),
        dataset=dataset,
        domain=domain,
        split=split,
        prompt=_require_prompt(dataset, index, prompt),
        gold_answer=normalize_answer(gold_answer),
        choices=choices or [],
        source="public",
        metadata=metadata or {},
    )


def convert_gsm8k_item(item: dict, index: int, split: str = "test") -> TaskRecord:
    answer = normalize_text(item.get("answer"))
    if "####" in answer:
        gold = answer.split("####", 1)[1].strip()
        method = "hash_delimiter"
    else:
        gold = answer
        method = "raw_answer"
    return _record(
        dataset="gsm8k",
        domain="math_reasoning",
        index=index,
        split=split,
        prompt=normalize_text(item.get("question")),
        gold_answer=gold,
        metadata={"raw_answer": answer, "answer_extraction_method": method},
    )


def convert_prontoqa_item(item: dict, index: int, split: str = "test") -> TaskRecord:
    prompt = normalize_text(item.get("question") or item.get("query") or item.get("prompt"))
    gold = item.get("answer", item.get("label", item.get("target")))
    return _record(
        dataset="prontoqa",
        domain="logic_reasoning",
        index=index,
        split=split,
        prompt=prompt,
        gold_answer=gold,
        metadata=compact_metadata(item, ["query", "target", "label", "answer"]),
    )


def convert_mmlu_item(item: dict, index: int, split: str = "test") -> TaskRecord:
    choices = normalize_choices(item.get("choices"))
    raw_answer = item.get("answer")
    if isinstance(raw_answer, int) and choices:
        gold = chr(ord("A") + raw_answer)
    else:
        gold = raw_answer
    return _record(
        dataset="mmlu",
        domain="knowledge_reasoning",
        index=index,
        split=split,
        prompt=normalize_text(item.get("question")),
        gold_answer=gold,
        choices=choices,
        metadata={"subject": normalize_text(item.get("subject")), "raw_answer": raw_answer},
    )


def convert_csqa_item(item: dict, index: int, split: str = "validation") -> TaskRecord:
    return _record(
        dataset="csqa",
        domain="commonsense_reasoning",
        index=index,
        split=split,
        prompt=normalize_text(item.get("question")),
        gold_answer=item.get("answerKey", item.get("answer")),
        choices=normalize_choices(item.get("choices")),
        metadata={
            "question_concept": normalize_text(item.get("question_concept")),
            "raw_answer": item.get("answerKey", item.get("answer")),
        },
    )


def convert_svamp_item(item: dict, index: int, split: str = "test") -> TaskRecord:
    body = normalize_text(item.get("Body") or item.get("body"))
    question = normalize_text(item.get("Question") or item.get("question"))
    prompt = "\n".join(part for part in [body, question] if part)
    return _record(
        dataset="svamp",
        domain="math_reasoning",
        index=index,
        split=split,
        prompt=prompt,
        gold_answer=item.get("Answer", item.get("answer")),
        metadata={"equation": normalize_text(item.get("Equation") or item.get("equation"))},
    )


def convert_multiarith_item(item: dict, index: int, split: str = "test") -> TaskRecord:
    return _record(
        dataset="multiarith",
        domain="math_reasoning",
        index=index,
        split=split,
        prompt=normalize_text(item.get("question")),
        gold_answer=item.get("final_ans", item.get("answer")),
        metadata={"equation": normalize_text(item.get("equation"))},
    )


def convert_aqua_item(item: dict, index: int, split: str = "test") -> TaskRecord:
    return _record(
        dataset="aqua",
        domain="math_reasoning",
        index=index,
        split=split,
        prompt=normalize_text(item.get("question")),
        gold_answer=item.get("correct"),
        choices=normalize_choices(item.get("options")),
        metadata=compact_metadata(item, ["rationale"], max_value_chars=500),
    )


def convert_humaneval_item(item: dict, index: int, split: str = "test") -> TaskRecord:
    return _record(
        dataset="humaneval",
        domain="code",
        index=index,
        split=split,
        prompt=normalize_text(item.get("prompt"), preserve_newlines=True),
        gold_answer=item.get("canonical_solution"),
        metadata=compact_metadata(item, ["task_id", "entry_point", "test"], max_value_chars=800)
        | {"source_task_id": normalize_text(item.get("task_id"))},
    )


def convert_mbpp_item(item: dict, index: int, split: str = "test") -> TaskRecord:
    prompt = normalize_text(item.get("text") or item.get("prompt"), preserve_newlines=True)
    return _record(
        dataset="mbpp",
        domain="code",
        index=index,
        split=split,
        prompt=prompt,
        gold_answer=item.get("code"),
        metadata=compact_metadata(item, ["task_id", "test_list", "test_setup_code"], max_value_chars=800)
        | {"source_task_id": normalize_text(item.get("task_id"))},
    )


CONVERTERS: dict[str, Callable[[dict, int, str], TaskRecord]] = {
    "gsm8k": convert_gsm8k_item,
    "prontoqa": convert_prontoqa_item,
    "mmlu": convert_mmlu_item,
    "csqa": convert_csqa_item,
    "svamp": convert_svamp_item,
    "multiarith": convert_multiarith_item,
    "aqua": convert_aqua_item,
    "humaneval": convert_humaneval_item,
    "mbpp": convert_mbpp_item,
}


def convert_public_item(dataset: str, item: dict, index: int, split: str) -> TaskRecord:
    if dataset not in CONVERTERS:
        raise ValueError(f"Unknown public dataset: {dataset}")
    try:
        return CONVERTERS[dataset](item, index, split)
    except Exception as exc:
        if isinstance(exc, ValueError) and f"{dataset} index {index}" in str(exc):
            raise
        raise ValueError(f"{dataset} index {index}: failed to convert item: {exc}") from exc


def convert_public_items(dataset: str, items: list[dict], split: str) -> list[TaskRecord]:
    return [convert_public_item(dataset, item, index, split) for index, item in enumerate(items)]
