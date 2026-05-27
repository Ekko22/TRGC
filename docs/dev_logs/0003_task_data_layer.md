# Task Data Layer and Manifest System

## Date time

2026-05-27 Asia/Shanghai

## Completed Work

- Added final task schema models for task records, anchors, task packets, and manifest entries.
- Added a fixed dataset registry for 9 public datasets and 2 synthetic local datasets.
- Added local JSONL loading and saving utilities.
- Added a HuggingFace loader stub that does not download datasets in this step.
- Added deterministic task anchor extraction for math, logic, choice, code, constraint, and local safety tasks.
- Added deterministic synthetic generators for Constraint MiniSet and Local-MAS Safety Set.
- Added deterministic sampling and task manifest construction.
- Added scripts for synthetic task creation and main manifest building.
- Added tests for schema validation, anchors, registry, synthetic data, sampling, and manifests.

## Design Boundaries

- No real LLM calls are made.
- No `/chat/completions` calls are made.
- No external network access or public dataset download is required.
- Generated `data/processed/` and `data/manifests/` artifacts are ignored by Git.
- SV remains outside task topology.
- This step does not add recovery, repair, regeneration, learned routing, risk classifier training, or fake G-Safeguard results.

## Files Changed

- `src/lmas_trgc/tasks/schema.py`
- `src/lmas_trgc/tasks/anchors.py`
- `src/lmas_trgc/tasks/loader.py`
- `src/lmas_trgc/tasks/dataset_sampler.py`
- `src/lmas_trgc/tasks/registry.py`
- `src/lmas_trgc/tasks/local_synthetic.py`
- `src/lmas_trgc/tasks/manifest.py`
- `scripts/create_synthetic_tasks.py`
- `scripts/build_task_manifest.py`
- `configs/datasets.yaml`
- `configs/experiment_main.yaml`
- `configs/experiment_pilot.yaml`
- `tests/test_task_schema.py`
- `tests/test_task_anchors.py`
- `tests/test_task_registry.py`
- `tests/test_task_manifest.py`
- `tests/test_synthetic_tasks.py`
- `README.md`

## Synthetic Task Generation

- Command: `conda run -n lmas-trgc python scripts/create_synthetic_tasks.py --output-dir data/processed/synthetic --overwrite`
- Expected output: 16 Constraint MiniSet tasks and 16 Local-MAS Safety Set tasks.
- Generated JSONL files are ignored by Git.

## Manifest Generation

- Command: `conda run -n lmas-trgc python scripts/build_task_manifest.py --output data/manifests/main_manifest.json`
- Expected behavior: build a manifest from available local tasks, record missing public datasets, and avoid embedding full prompts.
- Generated manifest files are ignored by Git.

## Test Result

- Command: `conda run -n lmas-trgc python -m pytest -q`
- Status: passed, `56 passed in 0.76s`.

## Execution Result

- Synthetic task generation: 16 Constraint MiniSet tasks and 16 Local-MAS Safety Set tasks.
- Manifest generation: 32 tasks from synthetic datasets.
- Missing public datasets: `gsm8k`, `prontoqa`, `mmlu`, `csqa`, `svamp`, `multiarith`, `aqua`, `humaneval`, `mbpp`.
- Generated data files are under ignored `data/processed/` and `data/manifests/` paths.

## Git Commit

- Commit message: `feat: add task data layer and manifest system`
- commit hash is reported in final execution summary
