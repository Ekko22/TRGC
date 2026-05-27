from __future__ import annotations

from pydantic import BaseModel

from lmas_trgc.judging.judge import JudgeOutcome
from lmas_trgc.logging.schemas import RunSummaryRecord


class StandardRunMetrics(BaseModel):
    run_id: str
    task_id: str
    dataset: str | None = None
    domain: str | None = None
    topology: str
    attack_type: str
    defense_name: str
    judge_mode: str
    valid_for_paper: bool
    clean_success: bool | None = None
    robust_success: bool | None = None
    attack_success: bool | None = None
    safety_violation: bool | None = None
    benign_drop_applicable: bool = False
    task_success: bool
    answer_correct: bool


def build_standard_run_metrics(
    run_summary: RunSummaryRecord,
    judge_outcome: JudgeOutcome,
) -> StandardRunMetrics:
    is_clean = run_summary.attack_type == "none"
    return StandardRunMetrics(
        run_id=run_summary.run_id,
        task_id=run_summary.task_id,
        dataset=run_summary.dataset,
        domain=run_summary.domain,
        topology=run_summary.topology,
        attack_type=run_summary.attack_type,
        defense_name=run_summary.defense_name,
        judge_mode=judge_outcome.judge_mode,
        valid_for_paper=judge_outcome.valid_for_paper,
        clean_success=judge_outcome.task_success if is_clean else None,
        robust_success=judge_outcome.robust_success if not is_clean else None,
        attack_success=judge_outcome.attack_success if not is_clean else None,
        safety_violation=judge_outcome.safety_violation,
        benign_drop_applicable=is_clean,
        task_success=judge_outcome.task_success,
        answer_correct=judge_outcome.answer_correct,
    )
