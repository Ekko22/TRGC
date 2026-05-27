# Judge and Standard Effect Metrics

## Date Time

2026-05-28 Asia/Shanghai

## Completed Work

- Added answer, number, choice, and final-answer normalization helpers.
- Added deterministic safety violation rules.
- Added judge contracts derived from `TaskPacket`.
- Added `RuleBasedJudge` and `MockProtocolJudge`.
- Added `final_output` to `SingleRunResult` for in-memory judging.
- Added standard run metrics for clean success, robust success, attack success, and safety violation.
- Added standard effect aggregation for Clean TSR, Robust TSR, ASR, SVR, and Benign Drop.
- Integrated optional judge outcome and standard metrics files into run artifacts.
- Integrated judge mode into Stage-B pilot and batch runners.
- Added standard metric aggregation CLI.

## Design Boundaries

- Judge does not call LLMs.
- Judge does not access the network.
- Judge does not modify run results.
- `mock_protocol` is for engineering validation only and is marked `valid_for_paper=false`.
- `rule_based` is the deterministic scoring mode intended for future real LLM outputs.
- Artifacts store hashes and structured outcomes, not final output text, final context text, prompts, API keys, or raw LLM responses.

## Judge Modes

- `mock_protocol`: treats completed mock pipeline execution as protocol success, checks safety rules, and marks outputs as not valid for paper.
- `rule_based`: compares final output against task answer contracts and safety contracts without external model calls.

## Standard Metrics

- Clean TSR / Accuracy.
- Robust TSR.
- ASR.
- SVR.
- Benign Drop.

## Artifact Integration

When judge output is available, run artifacts include:

- `judge_outcome.json`
- `standard_metrics.json`

These files coexist with the previous propagation and routing metrics.

## Batch Aggregation

`scripts/aggregate_standard_metrics.py` reads `standard_metrics.json` from batch run artifacts and produces overall and grouped effect metrics.

## Tests

- Command: `conda run -n lmas-trgc python -m pytest -q`
- Status: passed, `144 passed in 8.71s`.

Validation commands:

- Single run judge artifact: `completed=true`, `judge_mode=mock_protocol`, `valid_for_paper=false`, `task_success=true`, `attack_success=true`.
- Artifact inspection: `inspect_run_artifact.py` validated `results/runs/stage_b/run_a2533c5936f250bc5afd`.
- Batch judge smoke: `16` total runs, `16` successful, `0` failed, `valid_for_paper_runs=0`.
- Standard metric aggregation: `clean_tsr=1.0`, `robust_tsr=0.0`, `asr=1.0`, `svr=0.0`.

## Git Commit

- Commit message: `feat: add judge and standard effect metrics`
- Commit hash is reported in final execution summary.
