from lmas_trgc.analysis.diagnostics import (
    DiagnosticRunRecord,
    analyze_attack_effectiveness,
    analyze_defense_comparison,
    analyze_sv_cost,
    analyze_trgc_actions,
    build_root_cause_decision,
    run_all_analyses,
)


def _record(
    *,
    run_id: str,
    attack_type: str = "none",
    defense_name: str = "no_defense",
    dataset: str = "gsm8k",
    task_success: bool = True,
    answer_correct: bool | None = None,
    attack_success: bool | None = None,
    robust_success: bool | None = None,
    attacked_messages: int = 0,
    blocked_messages: int = 0,
    downweighted_messages: int = 0,
    rerouted_messages: int = 0,
    total_llm_calls: int = 11,
    total_tokens: int = 100,
) -> DiagnosticRunRecord:
    if answer_correct is None:
        answer_correct = task_success
    return DiagnosticRunRecord(
        run_id=run_id,
        task_id=f"task_{run_id}",
        dataset=dataset,
        topology="graph",
        attack_type=attack_type,
        defense_name=defense_name,
        completed=True,
        total_messages=11,
        delivered_messages=11 - blocked_messages,
        attacked_messages=attacked_messages,
        blocked_messages=blocked_messages,
        downweighted_messages=downweighted_messages,
        rerouted_messages=rerouted_messages,
        total_llm_calls=total_llm_calls,
        total_tokens=total_tokens,
        judge_mode="rule_based",
        valid_for_paper=True,
        task_success=task_success,
        answer_correct=answer_correct,
        safety_violation=False,
        attack_success=attack_success,
        robust_success=robust_success,
        clean_success=task_success if attack_type == "none" else None,
        expected_answer="42",
        predicted_answer="wrong" if not answer_correct else "42",
        metric="exact_match",
        final_context_hash="ctx",
        final_output_hash="out",
        artifact_dir=f"/tmp/{run_id}",
        summary_fields=["run_id", "total_llm_calls"],
        metrics_fields=["run_id", "total_llm_calls"],
    )


def test_clean_baseline_low_blocks_scaling():
    records = [
        _record(run_id="clean_fail_1", task_success=False),
        _record(run_id="clean_fail_2", task_success=False),
        _record(run_id="clean_ok", task_success=True),
        _record(run_id="trgc_attack", attack_type="message_poisoning", defense_name="trgc", attack_success=True, robust_success=False, attacked_messages=2),
        _record(run_id="no_def_attack", attack_type="message_poisoning", defense_name="no_defense", attack_success=True, robust_success=False, attacked_messages=2),
    ]
    analyses = run_all_analyses(records)
    decision = analyses["root_cause_decision"]
    assert analyses["clean_baseline"]["clean_tsr"] < 0.6
    assert decision["should_scale_experiment"] is False
    assert decision["should_modify_judge"] is True
    assert decision["should_modify_prompt_contract"] is True


def test_sv_cost_likely_missing_when_full_checking_calls_match_no_defense():
    records = [
        _record(run_id="no_def", defense_name="no_defense", total_llm_calls=11),
        _record(run_id="full", defense_name="full_checking_light", total_llm_calls=11, downweighted_messages=11, rerouted_messages=11),
    ]
    analysis = analyze_sv_cost(records)
    assert analysis["sv_cost_likely_missing"] is True
    assert "artifact_metrics_or_summary_sv_fields" in analysis["missing_fields"]


def test_trgc_actions_with_attack_success_records_ineffective_intervention():
    record = _record(
        run_id="trgc_bad",
        attack_type="message_poisoning",
        defense_name="trgc",
        attack_success=True,
        robust_success=False,
        attacked_messages=2,
        blocked_messages=1,
    )
    analysis = analyze_trgc_actions([record])
    assert len(analysis["ineffective_intervention_cases"]) == 1


def test_message_poisoning_with_zero_attacked_messages_records_attack_missing():
    record = _record(
        run_id="missing_attack",
        attack_type="message_poisoning",
        defense_name="no_defense",
        attack_success=False,
        robust_success=True,
        attacked_messages=0,
    )
    analysis = analyze_attack_effectiveness([record])
    assert len(analysis["attack_missing_errors"]) == 1


def test_defense_comparison_calculates_no_defense_vs_trgc():
    records = [
        _record(run_id="no_def_clean", defense_name="no_defense", task_success=True),
        _record(run_id="trgc_clean", defense_name="trgc", task_success=True),
        _record(
            run_id="no_def_attack",
            attack_type="message_poisoning",
            defense_name="no_defense",
            attack_success=True,
            robust_success=False,
            attacked_messages=2,
        ),
        _record(
            run_id="trgc_attack",
            attack_type="message_poisoning",
            defense_name="trgc",
            attack_success=False,
            robust_success=True,
            attacked_messages=2,
            blocked_messages=1,
        ),
    ]
    analysis = analyze_defense_comparison(records)
    assert analysis["no_defense_vs_trgc"] is not None
    assert analysis["whether_trgc_improves_asr"] is True


def test_root_cause_decision_prefers_judge_prompt_when_clean_tsr_low():
    records = [
        _record(run_id="clean_fail", task_success=False),
        _record(run_id="attack", attack_type="message_poisoning", defense_name="trgc", attack_success=True, robust_success=False, attacked_messages=2),
    ]
    decision = build_root_cause_decision(run_all_analyses(records))
    assert decision["should_scale_experiment"] is False
    assert decision["should_modify_judge"] is True
    assert decision["should_modify_prompt_contract"] is True
    assert decision["decision_label"] == "B"
