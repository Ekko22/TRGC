# Data Quality Audit

## Date time

2026-05-28T05:35:13.080723+00:00

## Scope

- Active datasets: 9 public datasets and 2 synthetic datasets.
- Expected manifest size: 104 tasks.
- Full prompts, code bodies, tests, and data rows are intentionally omitted.

## Overall Status

- overall_status: `pass`
- total_errors: 0
- total_warnings: 0

## Dataset Counts

| Dataset | Count | Target | Ready | Errors | Warnings |
|---|---:|---:|---|---:|---:|
| gsm8k | 8 | 8 | True | 0 | 0 |
| prontoqa | 8 | 8 | True | 0 | 0 |
| mmlu | 8 | 8 | True | 0 | 0 |
| csqa | 8 | 8 | True | 0 | 0 |
| svamp | 8 | 8 | True | 0 | 0 |
| multiarith | 8 | 8 | True | 0 | 0 |
| aqua | 8 | 8 | True | 0 | 0 |
| humaneval | 8 | 8 | True | 0 | 0 |
| mbpp | 8 | 8 | True | 0 | 0 |
| constraint_miniset | 16 | 16 | True | 0 | 0 |
| local_mas_safety | 16 | 16 | True | 0 | 0 |

## Manifest Validation

- manifest_total_tasks: 104
- expected_total_tasks: 104
- missing_datasets: []

## Anchor and Attack Surface Validation

- checked_tasks: 104
- anchor_errors: 0
- anchor_warnings: 0

## Errors

- none

## Warnings

- none

## Sample Summaries

### gsm8k

- task_id=`gsm8k_test_00000`, prompt_chars=280, gold_answer_preview=`18`, choices_count=0, anchors_count=3, target_slots_count=1, metadata_keys=['answer_extraction_method', 'answer_format', 'attack_surfaces', 'judge_type', 'raw_answer', 'target_slots', 'task_anchors']
- task_id=`gsm8k_test_00001`, prompt_chars=104, gold_answer_preview=`3`, choices_count=0, anchors_count=2, target_slots_count=1, metadata_keys=['answer_extraction_method', 'answer_format', 'attack_surfaces', 'judge_type', 'raw_answer', 'target_slots', 'task_anchors']

### prontoqa

- task_id=`prontoqa_test_00000`, prompt_chars=111, gold_answer_preview=`true`, choices_count=2, anchors_count=3, target_slots_count=1, metadata_keys=['answer_format', 'attack_surfaces', 'attackable_link', 'gold_label', 'judge_type', 'rule_chain', 'target_property', 'target_slots', 'task_anchors']
- task_id=`prontoqa_test_00001`, prompt_chars=108, gold_answer_preview=`false`, choices_count=2, anchors_count=3, target_slots_count=1, metadata_keys=['answer_format', 'attack_surfaces', 'attackable_link', 'gold_label', 'judge_type', 'rule_chain', 'target_property', 'target_slots', 'task_anchors']

### mmlu

- task_id=`mmlu_test_00000`, prompt_chars=83, gold_answer_preview=`B`, choices_count=4, anchors_count=5, target_slots_count=1, metadata_keys=['answer_format', 'attack_surfaces', 'judge_type', 'raw_answer', 'subject', 'target_slots', 'task_anchors']
- task_id=`mmlu_test_00001`, prompt_chars=65, gold_answer_preview=`C`, choices_count=4, anchors_count=5, target_slots_count=1, metadata_keys=['answer_format', 'attack_surfaces', 'judge_type', 'raw_answer', 'subject', 'target_slots', 'task_anchors']

### csqa

- task_id=`csqa_validation_00000`, prompt_chars=108, gold_answer_preview=`A`, choices_count=5, anchors_count=6, target_slots_count=1, metadata_keys=['answer_format', 'attack_surfaces', 'judge_type', 'question_concept', 'raw_answer', 'target_slots', 'task_anchors']
- task_id=`csqa_validation_00001`, prompt_chars=33, gold_answer_preview=`A`, choices_count=5, anchors_count=6, target_slots_count=1, metadata_keys=['answer_format', 'attack_surfaces', 'judge_type', 'question_concept', 'raw_answer', 'target_slots', 'task_anchors']

### svamp

- task_id=`svamp_test_00000`, prompt_chars=131, gold_answer_preview=`51`, choices_count=0, anchors_count=3, target_slots_count=1, metadata_keys=['answer_format', 'attack_surfaces', 'equation', 'judge_type', 'target_slots', 'task_anchors']
- task_id=`svamp_test_00001`, prompt_chars=114, gold_answer_preview=`1`, choices_count=0, anchors_count=3, target_slots_count=1, metadata_keys=['answer_format', 'attack_surfaces', 'equation', 'judge_type', 'target_slots', 'task_anchors']

### multiarith

- task_id=`multiarith_test_00000`, prompt_chars=148, gold_answer_preview=`10`, choices_count=0, anchors_count=6, target_slots_count=1, metadata_keys=['answer_format', 'attack_surfaces', 'equation', 'judge_type', 'target_slots', 'task_anchors']
- task_id=`multiarith_test_00001`, prompt_chars=149, gold_answer_preview=`17`, choices_count=0, anchors_count=4, target_slots_count=1, metadata_keys=['answer_format', 'attack_surfaces', 'equation', 'judge_type', 'target_slots', 'task_anchors']

### aqua

- task_id=`aqua_test_00000`, prompt_chars=188, gold_answer_preview=`B`, choices_count=5, anchors_count=7, target_slots_count=1, metadata_keys=['answer_format', 'attack_surfaces', 'judge_type', 'target_slots', 'task_anchors']
- task_id=`aqua_test_00001`, prompt_chars=376, gold_answer_preview=`C`, choices_count=5, anchors_count=8, target_slots_count=1, metadata_keys=['answer_format', 'attack_surfaces', 'judge_type', 'target_slots', 'task_anchors']

### humaneval

- task_id=`humaneval_test_00000`, prompt_chars=317, gold_answer_preview=`for idx, elem in enumerate(numbers):
        for idx2, elem2 in enumerate(number`, choices_count=0, anchors_count=3, target_slots_count=1, metadata_keys=['answer_format', 'attack_surfaces', 'entry_point', 'judge_type', 'source_task_id', 'target_slots', 'task_anchors', 'task_id', 'test', 'tests']
- task_id=`humaneval_test_00001`, prompt_chars=475, gold_answer_preview=`result = []
    current_string = []
    current_depth = 0

    for c in paren_st`, choices_count=0, anchors_count=4, target_slots_count=1, metadata_keys=['answer_format', 'attack_surfaces', 'entry_point', 'judge_type', 'source_task_id', 'target_slots', 'task_anchors', 'task_id', 'test', 'tests']

### mbpp

- task_id=`mbpp_test_00000`, prompt_chars=97, gold_answer_preview=`def remove_Occ(s,ch): 
    for i in range(len(s)): 
        if (s[i] == ch): `, choices_count=0, anchors_count=1, target_slots_count=1, metadata_keys=['answer_format', 'attack_surfaces', 'challenge_test_list', 'judge_type', 'source_task_id', 'target_slots', 'task_anchors', 'task_id', 'test_list', 'test_setup_code', 'tests']
- task_id=`mbpp_test_00001`, prompt_chars=92, gold_answer_preview=`def sort_matrix(M):
    result = sorted(M, key=sum)
    return result`, choices_count=0, anchors_count=1, target_slots_count=1, metadata_keys=['answer_format', 'attack_surfaces', 'challenge_test_list', 'judge_type', 'source_task_id', 'target_slots', 'task_anchors', 'task_id', 'test_list', 'test_setup_code', 'tests']

### constraint_miniset

- task_id=`constraint_miniset_001`, prompt_chars=458, gold_answer_preview=`denied`, choices_count=0, anchors_count=5, target_slots_count=3, metadata_keys=['allowed_actions', 'answer_format', 'attack_flip_value', 'attack_surfaces', 'case_facts', 'constraint_type', 'constraints', 'decisive_gate', 'forbidden_actions', 'gold_gate_value', 'judge_type', 'policy_rules', 'target_slots', 'task_anchors', 'violation_types']
- task_id=`constraint_miniset_002`, prompt_chars=475, gold_answer_preview=`allowed`, choices_count=0, anchors_count=5, target_slots_count=3, metadata_keys=['allowed_actions', 'answer_format', 'attack_flip_value', 'attack_surfaces', 'case_facts', 'constraint_type', 'constraints', 'decisive_gate', 'forbidden_actions', 'gold_gate_value', 'judge_type', 'policy_rules', 'target_slots', 'task_anchors', 'violation_types']

### local_mas_safety

- task_id=`local_mas_safety_001`, prompt_chars=590, gold_answer_preview=`safe`, choices_count=0, anchors_count=10, target_slots_count=3, metadata_keys=['allowed_actions', 'allowed_paths', 'answer_format', 'attack_surfaces', 'forbidden_actions', 'forbidden_paths', 'judge_type', 'required_review_steps', 'scenario_type', 'target_slots', 'task_anchors', 'unsafe_target_action', 'violation_types']
- task_id=`local_mas_safety_002`, prompt_chars=550, gold_answer_preview=`unsafe`, choices_count=0, anchors_count=10, target_slots_count=3, metadata_keys=['allowed_actions', 'allowed_paths', 'answer_format', 'attack_surfaces', 'forbidden_actions', 'forbidden_paths', 'judge_type', 'required_review_steps', 'scenario_type', 'target_slots', 'task_anchors', 'unsafe_target_action', 'violation_types']

## Decision

The 104-task manifest is accepted for the next experimental stage.

## Git Commit

commit hash is reported in final execution summary
