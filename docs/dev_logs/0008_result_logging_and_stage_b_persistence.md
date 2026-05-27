# Result Logging and Stage-B Persistence

## Date Time

2026-05-28 Asia/Shanghai

## Completed Work

- Added structured logging schemas for run summaries, message events, topology events, metrics, and artifact manifests.
- Added `RunArtifactWriter` for Stage-B run artifact directories.
- Added `artifact_loader` validation and load helpers.
- Added metrics calculation from `SingleRunResult`.
- Added run summary conversion helpers that hash final context instead of storing it.
- Updated Stage-B pilot with optional `--save-artifact`, `--output-root`, and `--overwrite`.
- Added `scripts/inspect_run_artifact.py` for artifact validation and inspection.
- Added tests for schemas, metrics, writer, loader, and Stage-B persistence.

## Design Boundaries

- Stage-B still uses `MockLLMClient` only.
- No real LLM calls, `/chat/completions`, `/models`, network access, or dataset downloads are used.
- Artifact writing is opt-in with `--save-artifact`; default Stage-B runs remain stdout-only.
- Artifacts do not store full prompts, final context text, API keys, raw LLM responses, or generated dataset files.
- Result persistence remains outside `SingleRunExecutor`; the executor returns structured results and the logging layer writes artifacts.

## Artifact Schema

Each saved Stage-B run writes:

- `run_summary.json`
- `message_events.jsonl`
- `message_events.csv`
- `topology_events.jsonl`
- `metrics.json`
- `config_snapshot.json`
- `README.md`
- `manifest.json`

The message event records keep route, gate, topology, and attack fields but do not persist full message content.

## Stage-B Persistence

Stage-B persistence is enabled with:

```bash
conda run -n lmas-trgc python scripts/run_stage_b_pilot.py --topology graph --attack message_poisoning --defense trgc --save-artifact --json
```

Artifacts are written under `results/runs/stage_b/<run_id>/`, which remains ignored by Git.

## Validation

`scripts/inspect_run_artifact.py` validates required files, parses structured records, checks run ID consistency, and verifies event counts against the run summary.

Stage-B artifact smoke:

- Command: `conda run -n lmas-trgc python scripts/run_stage_b_pilot.py --topology graph --attack message_poisoning --defense trgc --save-artifact --json`
- Result: completed with `13` total messages, `4` attacked messages, and artifact directory `results/runs/stage_b/run_a2533c5936f250bc5afd`.
- Inspect command: `conda run -n lmas-trgc python scripts/inspect_run_artifact.py results/runs/stage_b/run_a2533c5936f250bc5afd`
- Inspect result: validation passed.

## Tests

- Command: `conda run -n lmas-trgc python -m pytest -q`
- Status: passed, `105 passed in 4.19s`.

## Git Commit

- Commit message: `feat: add stage-b result artifact logging`
- Commit hash is reported in final execution summary.
