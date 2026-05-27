# Stage-B Batch Runner and Artifact Aggregation

## Date Time

2026-05-28 Asia/Shanghai

## Completed Work

- Added `TaskResolver` for synthetic, processed JSONL, and manifest-backed task selection.
- Added `StageBBatchRunner` for mock-only Stage-B task/topology/attack/defense matrices.
- Added `StageBBatchWriter` for batch summaries, run indexes, aggregate metrics, manifests, and README files.
- Added pure-Python batch aggregation utilities.
- Added `scripts/run_stage_b_batch.py` for controlled batch execution.
- Added `scripts/aggregate_stage_b_artifacts.py` for batch artifact aggregation.
- Added tests for resolver, batch runner, batch writer, aggregation, and CLI scripts.

## Design Boundaries

- Stage-B batch remains mock-only.
- No real LLM calls, `/chat/completions`, `/models`, network access, or dataset downloads are used.
- Batch runner reuses `SingleRunExecutor` and `RunArtifactWriter`.
- Batch aggregation reads metrics records only and does not read prompts or final context text.
- Generated `results/runs/` artifacts remain ignored by Git.

## Task Resolver

The resolver supports three modes:

- `synthetic`: built-in Constraint MiniSet and Local-MAS Safety Set generators.
- `processed`: local `data/processed/public` or `data/processed/synthetic` JSONL.
- `manifest`: manifest entries resolved back to processed JSONL by `task_id`.

Manifest mode never reconstructs tasks from manifest metadata alone.

## Batch Runner

The Stage-B batch runner iterates over tasks, topologies, attacks, and defenses. Each run creates a stable run id, executes through `SingleRunExecutor`, and persists a standard run artifact.

## Batch Artifacts

Batch directories are written under `results/runs/stage_b_batches/<batch_id>/` and contain `batch_summary.json`, `run_index.jsonl`, `aggregate_metrics.json`, `aggregate_metrics.csv`, `README.md`, and `manifest.json`.

## Aggregation

Aggregation loads each run artifact through the artifact loader, reads `metrics.json`, and computes overall and grouped summaries without pandas.

## Tests

- Command: `conda run -n lmas-trgc python -m pytest -q`
- Status: passed, `118 passed in 6.05s`.

Validation commands:

- Dry-run: `4` tasks and `8` planned runs.
- Default batch: `8` total runs, `8` successful, `0` failed.
- Aggregate: `8` aggregated runs and grouped metrics.
- Matrix smoke: `96` total runs, `96` successful, `0` failed.

## Git Commit

- Commit message: `feat: add stage-b batch runner and aggregation`
- Commit hash is reported in final execution summary.
