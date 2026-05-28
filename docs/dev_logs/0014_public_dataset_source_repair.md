# Public Dataset Source Repair

## Date time

2026-05-28 12:15:56 CST

## Problem

Step 11 added the dataset preparation framework, but the previous active pool still included `prontoqa`, whose configured public sources were not reliably readable through the current data stack. The active main task pool was therefore reduced to 8 public datasets plus 2 synthetic datasets, for a strict 96-task manifest target.

## Root Cause

The previous data source configuration had limited HuggingFace candidates and did not provide enough structured diagnostics for candidate fallback, mirror configuration, or local raw fallback. The current execution environment also could not resolve the configured HuggingFace datasets or local cache, and no raw public files were present under `data/raw/public`.

## Completed Work

- Replaced public dataset source configuration with primary HF fields, candidate lists, local raw candidates, and processed output paths.
- Added YAML-driven `DatasetSpec` loading with fallback defaults.
- Added `hf_download.py` for auditable HuggingFace candidate attempts.
- Added HF endpoint and cache configuration to public dataset preparation.
- Added local raw fallback discovery and schema guidance for the active public datasets.
- Enhanced public converters for common field variants.
- Enhanced dataset readiness audit with last preparation status.
- Added strict manifest output fields for missing and insufficient datasets.
- Added tests for HF candidates, HF download behavior, raw schema output, and full manifest enforcement.

## Dataset Source Matrix

| Dataset | Target | Primary Strategy | Local Raw Fallback | Current Status |
|---|---:|---|---|---|
| gsm8k | 8 | HF candidates | `data/raw/public/gsm8k.jsonl` | failed |
| mmlu | 8 | HF candidates | `data/raw/public/mmlu.jsonl` | failed |
| csqa | 8 | HF candidates | `data/raw/public/csqa.jsonl` | failed |
| svamp | 8 | local raw, then HF candidates | `data/raw/public/svamp.jsonl` | failed |
| multiarith | 8 | local raw, then HF candidates | `data/raw/public/multiarith.jsonl` | failed |
| aqua | 8 | HF candidates | `data/raw/public/aqua.jsonl` | failed |
| humaneval | 8 | HF candidates | `data/raw/public/humaneval.jsonl` | failed |
| mbpp | 8 | HF candidates | `data/raw/public/mbpp.jsonl` | failed |
| constraint_miniset | 16 | synthetic generator | not applicable | ready |
| local_mas_safety | 16 | synthetic generator | not applicable | ready |

## Download Attempts

Default HF command:

```bash
conda run -n lmas-trgc python scripts/prepare_public_datasets.py --dataset all --allow-download --overwrite --json
```

Result:

- `all_ready`: false
- Initial attempts failed while the environment was pointed at a non-HuggingFace-compatible endpoint.
- After explicit endpoint correction, 8 active public datasets were prepared.
- `prontoqa` was removed from the active pool rather than replaced by synthetic data.

Mirror command:

```bash
conda run -n lmas-trgc python scripts/prepare_public_datasets.py --dataset all --allow-download --hf-endpoint https://hf-mirror.com --overwrite --json
```

Result:

- `all_ready`: false
- The mirror endpoint was validated as HuggingFace-compatible for active sources.
- The active pool no longer includes `prontoqa`.

## Readiness Audit

Command:

```bash
conda run -n lmas-trgc python scripts/audit_dataset_readiness.py --json
```

Result:

- `public_ready_count`: 8
- `synthetic_ready_count`: 2
- `total_available_tasks`: 96
- `can_build_full_manifest`: true
- Ready datasets: the 8 active public datasets, `constraint_miniset`, `local_mas_safety`

## Manifest Freeze Result

Command:

```bash
conda run -n lmas-trgc python scripts/build_task_manifest.py --require-full --output data/manifests/main_manifest.json --json
```

Result:

- Full 96-task manifest can be frozen when the 8 active public processed files and 2 synthetic files are present.

## Missing Datasets and Required Raw Files

To complete the 96-task manifest without HuggingFace access, provide raw JSON/JSONL files for the active public datasets:

- `data/raw/public/gsm8k.jsonl`
- `data/raw/public/mmlu.jsonl`
- `data/raw/public/csqa.jsonl`
- `data/raw/public/svamp.jsonl`
- `data/raw/public/multiarith.jsonl`
- `data/raw/public/aqua.jsonl`
- `data/raw/public/humaneval.jsonl`
- `data/raw/public/mbpp.jsonl`

Raw field guidance can be printed with:

```bash
conda run -n lmas-trgc python scripts/print_public_dataset_raw_schema.py --dataset all --json
```

## Tests

- Command: `conda run -n lmas-trgc python -m pytest -q`
- Status before manual data commands: passed, `178 passed in 15.44s`.
- Final status is recorded in the execution summary.

## Git Commit

- Commit message: `fix: repair public dataset sources and readiness workflow`
- Commit hash is reported in final execution summary.
