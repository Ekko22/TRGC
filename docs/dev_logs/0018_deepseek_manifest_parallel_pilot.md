# DeepSeek Manifest Parallel Pilot

## 1. Date time

2026-05-28 17:42:32 CST

## 2. Purpose

Run a small real DeepSeek engineering pilot over the current `main_v2_104` active manifest using the run-level parallel Stage-C manifest pilot runner.

## 3. Preconditions

- Git worktree was clean before the run.
- Full pytest passed before the run: `211 passed in 47.73s`.
- Real LLM execution was explicitly enabled with `--confirm-real-llm`.
- No dataset download was performed.
- No changes were made to attacks, defenses, TRGC, SV, topology, protocol, judge, active dataset pool, or manifest logic.

## 4. Configuration

- batch_id: `stage_c_manifest_parallel_clean_22`
- manifest_id: `main_v2_104`
- tasks_per_dataset: `1`
- selected_tasks: `11`
- topology: `graph`
- attack: `message_poisoning`
- defenses: `no_defense`, `trgc`
- max_steps: `3`
- max_workers: `2`
- sv_mode: `client`
- judge_mode: `rule_based`
- task agent model slot: `M1`
- task agent model name: `deepseek-v4-flash`

## 5. Data Quality Check

`conda run -n lmas-trgc python scripts/audit_task_quality.py --require-full --json`

- overall_status: `pass`
- active_dataset_count: `11`
- manifest_id: `main_v2_104`
- manifest_total_tasks: `104`
- errors: `0`
- warnings: `0`
- active datasets: `gsm8k`, `prontoqa`, `mmlu`, `csqa`, `svamp`, `multiarith`, `aqua`, `humaneval`, `mbpp`, `constraint_miniset`, `local_mas_safety`

## 6. Dry-run Result

`conda run -n lmas-trgc python scripts/run_stage_c_deepseek_manifest_pilot.py --dry-run --max-workers 2 --json`

- did_call_real_llm: `false`
- selected_tasks: `11`
- total_runs: `22`
- max_workers: `2`
- topology: `graph`
- attack: `message_poisoning`
- defenses: `no_defense`, `trgc`

## 7. Real Pilot Result

`conda run -n lmas-trgc python scripts/run_stage_c_deepseek_manifest_pilot.py --confirm-real-llm --batch-id stage_c_manifest_parallel_clean_22 --tasks-per-dataset 1 --topologies graph --attacks message_poisoning --defenses no_defense,trgc --max-steps 3 --max-workers 2 --sv-mode client --overwrite --json`

- batch_id: `stage_c_manifest_parallel_clean_22`
- manifest_id: `main_v2_104`
- selected_tasks: `11`
- selected_datasets: `gsm8k`, `prontoqa`, `mmlu`, `csqa`, `svamp`, `multiarith`, `aqua`, `humaneval`, `mbpp`, `constraint_miniset`, `local_mas_safety`
- topology: `graph`
- attack: `message_poisoning`
- defenses: `no_defense`, `trgc`
- max_steps: `3`
- max_workers: `2`
- sv_mode: `client`
- total_runs: `22`
- successful_runs: `22`
- failed_runs: `0`
- total_messages: `242`
- total_attacked_messages: `44`
- total_llm_calls: `242`
- total_input_tokens: `129648`
- total_output_tokens: `139453`
- total_tokens: `269101`
- batch_dir: `results/runs/stage_c_manifest_batches/stage_c_manifest_parallel_clean_22`
- completed: `true`
- warnings: `[]`

## 8. Aggregate Metrics

Dataset plus defense aggregate:

- total_runs: `22`
- total_messages: `242`
- total_attacked_messages: `44`
- total_llm_calls: `242`
- total_tokens: `269101`
- clean_tsr: `null`
- robust_tsr: `0.22727272727272727`
- asr: `0.7727272727272727`
- svr: `0.0`
- groups: `22`

Defense aggregate:

- no_defense summary: `n=11`, `robust_tsr=0.2727272727272727`, `asr=0.7272727272727273`, `svr=0.0`
- trgc summary: `n=11`, `robust_tsr=0.18181818181818182`, `asr=0.8181818181818182`, `svr=0.0`
- total_tokens: `269101`
- total_llm_calls: `242`

## 9. Artifact Validation

All `22` run artifacts listed in `run_index.jsonl` were validated with `scripts/inspect_run_artifact.py`.

- validated: `22`
- failed: `0`

## 10. Cost Summary

- total_llm_calls: `242`
- total_input_tokens: `129648`
- total_output_tokens: `139453`
- total_tokens: `269101`
- Monetary cost was not computed because no billing API or account statement was queried.

## 11. Interpretation

This is a small real engineering pilot, not a paper main experiment result. Each of the 11 datasets contributes only one selected task, so the run cannot support stable statistical conclusions. The run validates the end-to-end path across real manifest data, real DeepSeek task-agent calls, SV client checks, message poisoning attack injection, no-defense/TRGC conditions, rule-based judge output, artifact writing, aggregate metrics, and run-level parallel execution.

## 12. Limitations

- Only `22` runs were executed.
- Only graph topology was used.
- Only message poisoning was used.
- Only `no_defense` and `trgc` were compared.
- Results are suitable for engineering validation only.

## 13. Decision

The DeepSeek manifest pilot is accepted as a clean engineering pilot.

## 14. Git Commit

commit hash is reported in final execution summary
