# Data Quality Audit

## Date time

2026-05-28T04:56:14.735564+00:00

## Scope

- Active datasets: 8 public datasets and 2 synthetic datasets.
- Expected manifest size: 96 tasks.
- Full prompts, code bodies, tests, and data rows are intentionally omitted.

## Overall Status

- overall_status: `warning`
- total_errors: 0
- total_warnings: 5

## Dataset Counts

| Dataset | Count | Target | Ready | Errors | Warnings |
|---|---:|---:|---|---:|---:|
| gsm8k | 8 | 8 | True | 0 | 0 |
| mmlu | 8 | 8 | True | 0 | 0 |
| csqa | 8 | 8 | True | 0 | 0 |
| svamp | 8 | 8 | True | 0 | 0 |
| multiarith | 8 | 8 | True | 0 | 0 |
| aqua | 8 | 8 | True | 0 | 0 |
| humaneval | 8 | 8 | True | 0 | 0 |
| mbpp | 8 | 8 | True | 0 | 0 |
| constraint_miniset | 16 | 16 | True | 0 | 5 |
| local_mas_safety | 16 | 16 | True | 0 | 0 |

## Manifest Validation

- manifest_total_tasks: 96
- expected_total_tasks: 96
- missing_datasets: []

## Anchor and Attack Surface Validation

- checked_tasks: 96
- anchor_errors: 0
- anchor_warnings: 0

## Errors

- none

## Warnings

- `duplicate_prompt` [constraint_miniset]: Normalized prompt is duplicated 4 times; sample task_ids=['constraint_miniset_001', 'constraint_miniset_006', 'constraint_miniset_011', 'constraint_miniset_016']
- `duplicate_prompt` [constraint_miniset]: Normalized prompt is duplicated 3 times; sample task_ids=['constraint_miniset_002', 'constraint_miniset_007', 'constraint_miniset_012']
- `duplicate_prompt` [constraint_miniset]: Normalized prompt is duplicated 3 times; sample task_ids=['constraint_miniset_003', 'constraint_miniset_008', 'constraint_miniset_013']
- `duplicate_prompt` [constraint_miniset]: Normalized prompt is duplicated 3 times; sample task_ids=['constraint_miniset_004', 'constraint_miniset_009', 'constraint_miniset_014']
- `duplicate_prompt` [constraint_miniset]: Normalized prompt is duplicated 3 times; sample task_ids=['constraint_miniset_005', 'constraint_miniset_010', 'constraint_miniset_015']

## Sample Summaries

### gsm8k

- task_id=`gsm8k_test_00000`, prompt_chars=280, gold_answer_preview=`18`, choices_count=0, anchors_count=3, target_slots_count=1, metadata_keys=['answer_extraction_method', 'raw_answer']
- task_id=`gsm8k_test_00001`, prompt_chars=104, gold_answer_preview=`3`, choices_count=0, anchors_count=2, target_slots_count=1, metadata_keys=['answer_extraction_method', 'raw_answer']

### mmlu

- task_id=`mmlu_test_00000`, prompt_chars=83, gold_answer_preview=`B`, choices_count=4, anchors_count=5, target_slots_count=1, metadata_keys=['raw_answer', 'subject']
- task_id=`mmlu_test_00001`, prompt_chars=65, gold_answer_preview=`C`, choices_count=4, anchors_count=5, target_slots_count=1, metadata_keys=['raw_answer', 'subject']

### csqa

- task_id=`csqa_validation_00000`, prompt_chars=108, gold_answer_preview=`A`, choices_count=5, anchors_count=6, target_slots_count=1, metadata_keys=['question_concept', 'raw_answer']
- task_id=`csqa_validation_00001`, prompt_chars=33, gold_answer_preview=`A`, choices_count=5, anchors_count=6, target_slots_count=1, metadata_keys=['question_concept', 'raw_answer']

### svamp

- task_id=`svamp_test_00000`, prompt_chars=131, gold_answer_preview=`51`, choices_count=0, anchors_count=3, target_slots_count=1, metadata_keys=['equation']
- task_id=`svamp_test_00001`, prompt_chars=114, gold_answer_preview=`1`, choices_count=0, anchors_count=3, target_slots_count=1, metadata_keys=['equation']

### multiarith

- task_id=`multiarith_test_00000`, prompt_chars=148, gold_answer_preview=`1`, choices_count=0, anchors_count=6, target_slots_count=1, metadata_keys=['equation']
- task_id=`multiarith_test_00001`, prompt_chars=149, gold_answer_preview=`17`, choices_count=0, anchors_count=4, target_slots_count=1, metadata_keys=['equation']

### aqua

- task_id=`aqua_test_00000`, prompt_chars=188, gold_answer_preview=`B`, choices_count=5, anchors_count=7, target_slots_count=1, metadata_keys=[]
- task_id=`aqua_test_00001`, prompt_chars=376, gold_answer_preview=`C`, choices_count=6, anchors_count=8, target_slots_count=1, metadata_keys=[]

### humaneval

- task_id=`humaneval_test_00000`, prompt_chars=317, gold_answer_preview=`for idx, elem in enumerate(numbers):
        for idx2, elem2 in enumerate(number`, choices_count=0, anchors_count=3, target_slots_count=1, metadata_keys=['entry_point', 'source_task_id', 'task_id', 'test']
- task_id=`humaneval_test_00001`, prompt_chars=475, gold_answer_preview=`result = []
    current_string = []
    current_depth = 0

    for c in paren_st`, choices_count=0, anchors_count=4, target_slots_count=1, metadata_keys=['entry_point', 'source_task_id', 'task_id', 'test']

### mbpp

- task_id=`mbpp_test_00000`, prompt_chars=97, gold_answer_preview=`def remove_Occ(s,ch): 
    for i in range(len(s)): 
        if (s[i] == ch): `, choices_count=0, anchors_count=1, target_slots_count=1, metadata_keys=['challenge_test_list', 'source_task_id', 'task_id', 'test_list', 'test_setup_code']
- task_id=`mbpp_test_00001`, prompt_chars=92, gold_answer_preview=`def sort_matrix(M):
    result = sorted(M, key=sum)
    return result`, choices_count=0, anchors_count=1, target_slots_count=1, metadata_keys=['challenge_test_list', 'source_task_id', 'task_id', 'test_list', 'test_setup_code']

### constraint_miniset

- task_id=`constraint_miniset_001`, prompt_chars=232, gold_answer_preview=`denied`, choices_count=0, anchors_count=5, target_slots_count=3, metadata_keys=['attack_flip_value', 'constraint_type', 'constraints', 'decisive_gate', 'gold_gate_value', 'violation_types']
- task_id=`constraint_miniset_002`, prompt_chars=243, gold_answer_preview=`allowed`, choices_count=0, anchors_count=5, target_slots_count=3, metadata_keys=['attack_flip_value', 'constraint_type', 'constraints', 'decisive_gate', 'gold_gate_value', 'violation_types']

### local_mas_safety

- task_id=`local_mas_safety_001`, prompt_chars=260, gold_answer_preview=`safe`, choices_count=0, anchors_count=8, target_slots_count=3, metadata_keys=['allowed_actions', 'allowed_paths', 'forbidden_actions', 'forbidden_paths', 'required_review_steps', 'unsafe_target_action', 'violation_types']
- task_id=`local_mas_safety_002`, prompt_chars=262, gold_answer_preview=`unsafe`, choices_count=0, anchors_count=8, target_slots_count=3, metadata_keys=['allowed_actions', 'allowed_paths', 'forbidden_actions', 'forbidden_paths', 'required_review_steps', 'unsafe_target_action', 'violation_types']

## Decision

The manifest is usable for pilot runs, but warnings should be reviewed before main experiments.

## Git Commit

commit hash is reported in final execution summary
