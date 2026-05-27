from __future__ import annotations

from lmas_trgc.judging.contracts import JudgeResult
from lmas_trgc.judging.normalizer import normalize_answer


def exact_match_judge(task_id: str, prediction: str, reference: str) -> JudgeResult:
    normalized = normalize_answer(prediction)
    is_correct = normalized == normalize_answer(reference)
    return JudgeResult(
        task_id=task_id,
        is_correct=is_correct,
        normalized_answer=normalized,
        score=1.0 if is_correct else 0.0,
    )
