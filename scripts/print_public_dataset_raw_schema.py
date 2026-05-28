#!/usr/bin/env python
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from lmas_trgc.tasks.registry import get_default_dataset_specs

PUBLIC_DATASETS = ["gsm8k", "prontoqa", "mmlu", "csqa", "svamp", "multiarith", "aqua", "humaneval", "mbpp"]


RAW_SCHEMAS: dict[str, dict] = {
    "gsm8k": {
        "accepted_fields": ["question", "answer", "prompt", "response", "final_answer"],
        "minimal_required_fields": ["question or prompt", "answer or response or final_answer"],
        "example_json_line": {"question": "What is 40 + 2?", "answer": "Reasoning #### 42"},
    },
    "prontoqa": {
        "accepted_fields": [
            "question",
            "query",
            "prompt",
            "answer",
            "label",
            "target",
            "choices",
            "rule_chain",
            "reasoning_chain",
            "target_property",
            "attackable_link",
            "gold_label",
        ],
        "minimal_required_fields": ["question or query or prompt", "answer or label or target"],
        "example_json_line": {
            "question": "If all dax things are blicket and the target is dax, is the target blicket?",
            "answer": "true",
            "rule_chain": ["dax -> blicket", "target is dax"],
            "target_property": "blicket",
            "attackable_link": "dax -> blicket",
            "gold_label": "true",
        },
    },
    "mmlu": {
        "accepted_fields": ["question", "choices", "answer", "subject", "A", "B", "C", "D", "E"],
        "minimal_required_fields": ["question", "answer"],
        "example_json_line": {"question": "Pick one.", "choices": ["a", "b", "c", "d"], "answer": 1},
    },
    "csqa": {
        "accepted_fields": ["question", "question_concept", "choices", "answerKey", "answer", "label"],
        "minimal_required_fields": ["question", "answerKey or answer or label"],
        "example_json_line": {
            "question": "Where do people read?",
            "choices": {"label": ["A"], "text": ["library"]},
            "answerKey": "A",
        },
    },
    "svamp": {
        "accepted_fields": ["Body", "body", "Question", "question", "Answer", "answer", "Result", "result", "Equation", "equation"],
        "minimal_required_fields": ["Body/body or Question/question", "Answer or answer or Result/result"],
        "example_json_line": {"Body": "A has 2 apples.", "Question": "Adds 3?", "Answer": 5},
    },
    "multiarith": {
        "accepted_fields": ["question", "sQuestion", "Question", "final_ans", "final_answer", "answer", "Answer", "lSolutions", "equation"],
        "minimal_required_fields": ["question or sQuestion or Question", "final_ans or final_answer or answer"],
        "example_json_line": {"question": "There are 2 and then 3 more. How many?", "final_ans": 5},
    },
    "aqua": {
        "accepted_fields": ["question", "prompt", "options", "choices", "correct", "answer", "completion", "rationale"],
        "minimal_required_fields": ["question or prompt", "correct or answer or completion"],
        "example_json_line": {"question": "Choose the answer.", "options": ["A. 1", "B. 2"], "correct": "B"},
    },
    "humaneval": {
        "accepted_fields": ["task_id", "prompt", "canonical_solution", "solution", "entry_point", "test", "tests"],
        "minimal_required_fields": ["prompt", "canonical_solution or solution"],
        "example_json_line": {"task_id": "HumanEval/0", "prompt": "def add(a, b):", "canonical_solution": " return a + b"},
    },
    "mbpp": {
        "accepted_fields": ["task_id", "text", "prompt", "code", "canonical_solution", "test_list", "challenge_test_list", "test_setup_code"],
        "minimal_required_fields": ["text or prompt", "code or canonical_solution"],
        "example_json_line": {"task_id": 1, "text": "Write a function.", "code": "def f(): return 1"},
    },
}


def _selected_datasets(name: str) -> list[str]:
    if name == "all":
        return PUBLIC_DATASETS
    if name not in PUBLIC_DATASETS:
        raise ValueError(f"Unsupported dataset {name!r}; expected all or one of {PUBLIC_DATASETS}")
    return [name]


def build_schema_payload(dataset: str) -> dict:
    specs = get_default_dataset_specs()
    schema = dict(RAW_SCHEMAS[dataset])
    schema["dataset"] = dataset
    schema["expected_raw_paths"] = specs[dataset].local_raw_candidates
    schema["processed_output_path"] = specs[dataset].processed_path
    return schema


def main() -> int:
    parser = argparse.ArgumentParser(description="Print accepted raw JSON/JSONL schemas for public datasets.")
    parser.add_argument("--dataset", default="all", choices=["all", *PUBLIC_DATASETS])
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    payload = {dataset: build_schema_payload(dataset) for dataset in _selected_datasets(args.dataset)}
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        for dataset, schema in payload.items():
            print(f"{dataset}")
            print(f"  accepted_fields: {', '.join(schema['accepted_fields'])}")
            print(f"  minimal_required_fields: {', '.join(schema['minimal_required_fields'])}")
            print(f"  expected_raw_paths: {', '.join(schema['expected_raw_paths'])}")
            print(f"  processed_output_path: {schema['processed_output_path']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
