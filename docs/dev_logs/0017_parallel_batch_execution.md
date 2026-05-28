# Parallel Batch Execution and Progress Reporting

## 1. Date time

2026-05-28 17:12:48 CST

## 2. Completed Work

- Added a shared parallel runner utility for independent run jobs.
- Added configurable `max_workers`, `show_progress`, and `fail_fast` options.
- Updated Stage-B batch execution to run independent runs in parallel.
- Updated Stage-C DeepSeek manifest pilot execution to use run-level parallelism.
- Added tqdm progress reporting on stderr.
- Added tests for parallel execution, failure recording, JSON stdout cleanliness, and script safety.

## 3. Design Boundaries

- Parallelism is only at run level.
- A single run's 7-agent protocol is not parallelized.
- Agent steps, message propagation, attack injection, TRGC gates, SV checks, judge behavior, topologies, and protocol semantics are unchanged.
- Batch-level indexes, summaries, aggregates, manifests, and README files are written only by the main thread.

## 4. Run-Level Parallelism

The main thread builds deterministic run specs with stable `run_order` values and unique stable `run_id` values. Each worker creates its own run executor inputs, writes only its own run artifact directory, and returns a run record. Results are sorted by `run_order` before aggregate files are written.

## 5. tqdm Progress

tqdm is enabled by default and writes to stderr. JSON output remains on stdout, so `--json` output is still parseable. Use `--no-progress` to disable progress reporting.

## 6. Stage-B Batch Changes

Stage-B batch now accepts `--max-workers`, `--no-progress`, and `--fail-fast`. Mock-only batches can use higher values such as `--max-workers 4` or `--max-workers 8`.

## 7. Stage-C Pilot Changes

Stage-C DeepSeek manifest pilot now accepts `--max-workers`, `--no-progress`, and `--fail-fast`. Real LLM pilots default to `--max-workers 2`; higher values should be used cautiously because they may trigger API rate limits.

## 8. Tests

Tests cover ordered results, concurrent execution, non-fail-fast failure recording, fail-fast behavior, error redaction, Stage-B artifact validation, run index ordering, and script JSON output.

## 9. Git Commit

commit hash is reported in final execution summary
