# DeepSeek Manifest Pilot

## Date time

2026-05-28 Asia/Shanghai

## Completed Work

- Added a manifest-backed Stage-C DeepSeek pilot runner.
- Added stable per-dataset task selection from `main_v2_104`.
- Added real DeepSeek single-model orchestration for A1-A7 task agents.
- Added Stage-C batch artifacts, run index writing, propagation aggregation, and standard metric aggregation.
- Added safety-focused CLI behavior for dry-run, config-only, and no-confirm refusal paths.

## Design Boundaries

- Real LLM calls require explicit `--confirm-real-llm`.
- Dry-run, config-only, and tests do not call chat APIs.
- No datasets are downloaded in this step.
- No full prompts, final outputs, final contexts, API keys, or raw LLM responses are persisted.
- SV remains a sidecar and is not added to topology or protocol.
- This is a small engineering pilot, not the 8320-run main experiment.

## Data Readiness

- Required manifest: `main_v2_104`.
- Required task count: 104.
- Required active pool: 9 public datasets plus 2 synthetic datasets, including ProntoQA.
- Data quality audit must pass before real pilot execution.

## Manifest Task Selection

- Default selection uses all active datasets.
- Default `tasks_per_dataset=1`, yielding 11 selected tasks.
- Selection is deterministic: entries are grouped by dataset, sorted by `task_id`, and the first N tasks per dataset are selected.
- Full `TaskRecord` objects are loaded from `data/processed`; the manifest is never used to reconstruct prompt text.

## Real LLM Safety Guardrails

- `--dry-run` resolves task selection and matrix size without chat calls.
- `--check-config-only` validates manifest and model configuration without chat calls.
- Missing `--confirm-real-llm` returns refusal instead of running.
- DeepSeek M1 is mapped to all task agents only inside the pilot runner.
- API keys are never printed.

## Pilot Matrix

- Default topology: `graph`.
- Default attack: `message_poisoning`.
- Default defenses: `no_defense,trgc`.
- Default `max_steps=3` so Graph direct-to-finalizer and high-value attack edges can be reached.
- Default run count: 11 datasets x 1 task x 1 topology x 1 attack x 2 defenses = 22 runs.

## SV Mode

- Default `sv_mode=client`.
- `sv_mode=mock` is available for explicit mock SV runs.
- `--allow-sv-mock-fallback` can use mock SV if client configuration is incomplete.

## Metrics and Artifacts

- Run artifacts are written under `results/runs/stage_c_manifest/<run_id>/`.
- Batch artifacts are written under `results/runs/stage_c_manifest_batches/<batch_id>/`.
- Batch outputs include run index, propagation metrics, standard effect metrics, README, and manifest.
- Aggregation is available through `scripts/aggregate_stage_c_manifest_pilot.py`.

## Tests

- Added manifest task selection tests.
- Added pilot config validation tests.
- Added script safety tests for dry-run, no-confirm refusal, and config-only modes.
- Added aggregate script tests using fake artifacts.
- Full pytest result is reported in final execution summary.

## Real Pilot Result

- Executed: yes
- did_call_real_llm: true
- batch_id: `stage_c_manifest_d3811351bd13`
- manifest_id: `main_v2_104`
- selected_tasks: 11
- selected_datasets: gsm8k, prontoqa, mmlu, csqa, svamp, multiarith, aqua, humaneval, mbpp, constraint_miniset, local_mas_safety
- topology: graph
- attack: message_poisoning
- defenses: no_defense, trgc
- max_steps: 3
- sv_mode: client
- total_runs: 22
- successful_runs: 21
- failed_runs: 1
- total_messages: 231
- total_attacked_messages: 42
- total_llm_calls: 231
- total_tokens: 265125
- batch_dir: `results/runs/stage_c_manifest_batches/stage_c_manifest_d3811351bd13`
- aggregate_status: passed

One run failed before artifact creation:

- run_id: `run_842e64c8ae49a0a4e18b`
- task_id: `constraint_miniset_001`
- defense: trgc
- error summary: `BadRequestError: Param Incorrect; Not supported model mimo-V2.5`

The failure is isolated to the configured SV client model path. The DeepSeek task-agent path completed for the successful runs, artifacts were written, and aggregation succeeded. A follow-up run should either correct the SV model served by the configured SV endpoint or explicitly use `--sv-mode mock` / `--allow-sv-mock-fallback` where appropriate for engineering validation.

## Git Commit

commit hash is reported in final execution summary
