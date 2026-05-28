from __future__ import annotations

from collections.abc import Callable
import re

from lmas_trgc.tasks.normalizers import (
    compact_metadata,
    make_public_task_id,
    normalize_answer,
    normalize_choices,
    normalize_text,
)
from lmas_trgc.tasks.schema import TaskRecord


def _require_prompt(dataset: str, index: int, prompt: str, available_fields: list[str] | None = None) -> str:
    if not prompt:
        fields = f"; available fields={available_fields}" if available_fields is not None else ""
        raise ValueError(f"{dataset} index {index}: missing prompt/question field{fields}")
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
    available_fields: list[str] | None = None,
) -> TaskRecord:
    return TaskRecord(
        task_id=make_public_task_id(dataset, split, index),
        dataset=dataset,
        domain=domain,
        split=split,
        prompt=_require_prompt(dataset, index, prompt, available_fields),
        gold_answer=normalize_answer(gold_answer),
        choices=choices or [],
        source="public",
        metadata=metadata or {},
    )


def _extract_lettered_choices_from_text(text: str) -> list[str]:
    matches = list(re.finditer(r"(?<![A-Za-z0-9])([A-E])[\).:]\s*", text))
    if len(matches) < 2:
        return []
    choices: list[str] = []
    for index, match in enumerate(matches):
        start = match.end()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        value = normalize_text(text[start:end])
        if value:
            choices.append(f"{match.group(1).upper()}. {value}")
    return choices


def convert_gsm8k_item(item: dict, index: int, split: str = "test") -> TaskRecord:
    answer_value = item.get("answer", item.get("response", item.get("final_answer")))
    answer = normalize_text(answer_value)
    if "####" in answer:
        gold = answer.split("####", 1)[1].strip()
        method = "hash_delimiter"
    elif item.get("final_answer") is not None:
        gold = item.get("final_answer")
        method = "final_answer"
    else:
        gold = answer
        method = "raw_answer"
    return _record(
        dataset="gsm8k",
        domain="math_reasoning",
        index=index,
        split=split,
        prompt=normalize_text(item.get("question") or item.get("prompt")),
        gold_answer=gold,
        metadata={"raw_answer": answer, "answer_extraction_method": method},
        available_fields=sorted(item),
    )


def convert_mmlu_item(item: dict, index: int, split: str = "test") -> TaskRecord:
    choices = normalize_choices(
        item.get("choices") or [item.get(label) for label in ["A", "B", "C", "D", "E"] if item.get(label)]
    )
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
        available_fields=sorted(item),
    )


def convert_csqa_item(item: dict, index: int, split: str = "validation") -> TaskRecord:
    return _record(
        dataset="csqa",
        domain="commonsense_reasoning",
        index=index,
        split=split,
        prompt=normalize_text(item.get("question")),
        gold_answer=item.get("answerKey", item.get("answer", item.get("label"))),
        choices=normalize_choices(item.get("choices")),
        metadata={
            "question_concept": normalize_text(item.get("question_concept")),
            "raw_answer": item.get("answerKey", item.get("answer", item.get("label"))),
        },
        available_fields=sorted(item),
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
        gold_answer=item.get("Answer", item.get("answer", item.get("Result", item.get("result")))),
        metadata={"equation": normalize_text(item.get("Equation") or item.get("equation"))},
        available_fields=sorted(item),
    )


def convert_multiarith_item(item: dict, index: int, split: str = "test") -> TaskRecord:
    prompt = normalize_text(item.get("question") or item.get("sQuestion") or item.get("Question"))
    answer = item.get("final_ans", item.get("final_answer", item.get("answer", item.get("lSolutions", item.get("Answer")))))
    if isinstance(answer, list) and answer:
        answer = answer[0]
    return _record(
        dataset="multiarith",
        domain="math_reasoning",
        index=index,
        split=split,
        prompt=prompt,
        gold_answer=answer,
        metadata={"equation": normalize_text(item.get("equation"))},
        available_fields=sorted(item),
    )


def convert_aqua_item(item: dict, index: int, split: str = "test") -> TaskRecord:
    prompt = normalize_text(item.get("question") or item.get("prompt"))
    option_fields = [item.get(label) for label in ["A", "B", "C", "D", "E"] if item.get(label)]
    choices = normalize_choices(item.get("options") or item.get("choices") or option_fields)
    if len(choices) < 2:
        choices = _extract_lettered_choices_from_text(prompt)
    return _record(
        dataset="aqua",
        domain="math_reasoning",
        index=index,
        split=split,
        prompt=prompt,
        gold_answer=item.get("correct", item.get("answer", item.get("completion", item.get("gold_answer")))),
        choices=choices,
        metadata=compact_metadata(item, ["rationale", "completion"], max_value_chars=500),
        available_fields=sorted(item),
    )


def convert_humaneval_item(item: dict, index: int, split: str = "test") -> TaskRecord:
    return _record(
        dataset="humaneval",
        domain="code",
        index=index,
        split=split,
        prompt=normalize_text(item.get("prompt"), preserve_newlines=True),
        gold_answer=item.get("canonical_solution", item.get("solution")),
        metadata=compact_metadata(item, ["task_id", "entry_point", "test", "tests"], max_value_chars=800)
        | {"source_task_id": normalize_text(item.get("task_id"))},
        available_fields=sorted(item),
    )


def convert_mbpp_item(item: dict, index: int, split: str = "test") -> TaskRecord:
    prompt = normalize_text(item.get("text") or item.get("prompt"), preserve_newlines=True)
    return _record(
        dataset="mbpp",
        domain="code",
        index=index,
        split=split,
        prompt=prompt,
        gold_answer=item.get("code", item.get("canonical_solution")),
        metadata=compact_metadata(
            item,
            ["task_id", "test_list", "challenge_test_list", "test_setup_code"],
            max_value_chars=800,
        )
        | {"source_task_id": normalize_text(item.get("task_id"))},
        available_fields=sorted(item),
    )


CONVERTERS: dict[str, Callable[[dict, int, str], TaskRecord]] = {
    "gsm8k": convert_gsm8k_item,
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
        fields = sorted(item)
        raise ValueError(f"{dataset} index {index}: failed to convert item: {exc}; available fields={fields}") from exc


def convert_public_items(dataset: str, items: list[dict], split: str) -> list[TaskRecord]:
    return [convert_public_item(dataset, item, index, split) for index, item in enumerate(items)]
