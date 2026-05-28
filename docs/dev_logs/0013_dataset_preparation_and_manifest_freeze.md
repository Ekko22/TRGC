# Dataset Preparation and Manifest Freeze

## Date time

2026-05-28 11:57:53 CST

## Completed Work

- Added full dataset readiness fields to dataset configuration and registry specs.
- Added download/import readiness reporting for public dataset preparation.
- Added dataset readiness audit script for public and synthetic sources.
- Added strict `--require-full` main manifest validation for the 104-task target.
- Added tests for dataset readiness, download configuration behavior, and full manifest requirements.

## Design Boundaries

- Public datasets are never replaced by synthetic data.
- Tests do not download datasets or access the network.
- The preparation scripts do not call LLMs, `/chat/completions`, or `/models`.
- Generated `data/raw`, `data/processed`, and `data/manifests` files remain outside Git.
- Manifest entries do not contain full prompts.

## Dataset Support Matrix

| Dataset | Target Count | Source Strategy | Status |
|---|---:|---|---|
| gsm8k | 8 | HuggingFace | failed |
| prontoqa | 8 | local raw first, then HF candidates | failed |
| mmlu | 8 | HuggingFace | failed |
| csqa | 8 | HuggingFace | failed |
| svamp | 8 | local raw first, then HF candidates | failed |
| multiarith | 8 | local raw first, then HF candidates | failed |
| aqua | 8 | HuggingFace | failed |
| humaneval | 8 | HuggingFace | failed |
| mbpp | 8 | HuggingFace | failed |
| constraint_miniset | 16 | synthetic generator | ready |
| local_mas_safety | 16 | synthetic generator | ready |

## Download / Import Results

Command:

```bash
conda run -n lmas-trgc python scripts/prepare_public_datasets.py --dataset all --allow-download --overwrite --json
```

Result:

- Script execution completed with exit code 0.
- No public dataset reached ready status.
- All 9 public datasets failed because the configured HuggingFace sources or local cache could not be resolved from the current environment, and no local raw files were present under `data/raw/public`.
- No synthetic data was used to replace public datasets.
- Readiness report was written to `data/manifests/public_dataset_readiness.json`, which is ignored by Git.

## Readiness Audit

Command:

```bash
conda run -n lmas-trgc python scripts/audit_dataset_readiness.py --json
```

Result:

- `public_ready_count`: 0
- `synthetic_ready_count`: 2
- `total_available_tasks`: 32
- `can_build_full_manifest`: false
- Ready datasets: `constraint_miniset`, `local_mas_safety`

## Manifest Freeze Result

Command:

```bash
conda run -n lmas-trgc python scripts/build_task_manifest.py --require-full --output data/manifests/main_manifest.json --json
```

Result:

- Exit code: 2
- `total_tasks`: 32
- `is_full_manifest`: false
- Full 104-task manifest was not frozen.
- Missing public datasets: `gsm8k`, `prontoqa`, `mmlu`, `csqa`, `svamp`, `multiarith`, `aqua`, `humaneval`, `mbpp`

## Missing or Failed Datasets

The following public datasets are still required before the main manifest can be frozen:

- `gsm8k`
- `prontoqa`
- `mmlu`
- `csqa`
- `svamp`
- `multiarith`
- `aqua`
- `humaneval`
- `mbpp`

Next safe data action: provide local raw JSON/JSONL files under `data/raw/public/<dataset>.jsonl` or rerun the download preparation command in an environment with reachable HuggingFace dataset access.

## Tests

- Command: `conda run -n lmas-trgc python -m pytest -q`
- Status before manual data commands: passed, `168 passed in 12.07s`.
- Final status is recorded in the execution summary.

## Git Commit

- Commit message: `feat: finalize dataset preparation and manifest readiness`
- Commit hash is reported in final execution summary.
