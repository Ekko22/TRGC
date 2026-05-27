from lmas_trgc.analysis.standard_metrics import build_standard_run_metrics
from lmas_trgc.judging.judge import JudgeOutcome
from lmas_trgc.logging.schemas import RunSummaryRecord


def _summary(attack_type: str) -> RunSummaryRecord:
    return RunSummaryRecord(
        run_id="run_standard",
        task_id="task_standard",
        dataset="local_mas_safety",
        domain="local_mas_safety",
        topology="graph",
        attack_type=attack_type,
        defense_name="trgc",
        completed=True,
        final_agent="A7",
        total_messages=1,
        delivered_messages=1,
        blocked_messages=0,
        downweighted_messages=0,
        rerouted_messages=0,
        attacked_messages=0,
        created_at="2026-05-28T00:00:00+00:00",
    )


def _outcome() -> JudgeOutcome:
    return JudgeOutcome(
        run_id="run_standard",
        task_id="task_standard",
        judge_mode="rule_based",
        valid_for_paper=True,
        task_success=True,
        answer_correct=True,
        safety_violation=False,
        attack_success=False,
        robust_success=True,
        metric="exact_match",
    )


def test_clean_run_sets_clean_success():
    metrics = build_standard_run_metrics(_summary("none"), _outcome())
    assert metrics.clean_success is True
    assert metrics.robust_success is None


def test_attack_run_sets_robust_and_attack_success():
    outcome = _outcome()
    outcome.attack_success = True
    outcome.robust_success = False
    metrics = build_standard_run_metrics(_summary("message_poisoning"), outcome)
    assert metrics.clean_success is None
    assert metrics.robust_success is False
    assert metrics.attack_success is True


def test_safety_violation_passed_through():
    outcome = _outcome()
    outcome.safety_violation = True
    metrics = build_standard_run_metrics(_summary("none"), outcome)
    assert metrics.safety_violation is True
