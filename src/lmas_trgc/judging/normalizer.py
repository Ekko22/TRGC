from __future__ import annotations


def normalize_answer(answer: str) -> str:
    return " ".join(answer.strip().lower().split())
