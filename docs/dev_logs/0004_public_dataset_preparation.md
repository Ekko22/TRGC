# Public Dataset Preparation Layer

## Date time

2026-05-27 Asia/Shanghai

## Completed Work

- Added public dataset normalizers for text, answers, choices, compact metadata, and stable public task IDs.
- Added converters for GSM8K, ProntoQA, MMLU, CSQA, SVAMP, MultiArith, AQuA, HumanEval, and MBPP.
- Added raw JSON/JSONL loading and public processed JSONL saving/loading utilities.
- Added `scripts/prepare_public_datasets.py` for offline-first public dataset preparation.
- Updated manifest loading behavior so processed public JSONL files are used when present.
- Added tests for public adapters, offline import script behavior, and manifest integration with public processed data.

## Design Boundaries

- Default commands do not access the network.
- Public datasets are not downloaded unless `--allow-download` is explicitly provided.
- No real LLM calls or `/chat/completions` calls are made.
- No API keys are printed.
- Generated `data/processed/public/` and `data/manifests/` files are ignored by Git.
- This step does not add recovery, repair, regeneration, learned routing, risk classifier training, or fake G-Safeguard results.

## Public Dataset Support Matrix

| Dataset | Source Type | Default Split | Converter |
|---|---|---|---|
| gsm8k | hf | test | `convert_gsm8k_item` |
| prontoqa | local_jsonl | test | `convert_prontoqa_item` |
| mmlu | hf | test | `convert_mmlu_item` |
| csqa | hf | validation | `convert_csqa_item` |
| svamp | local_jsonl | test | `convert_svamp_item` |
| multiarith | local_jsonl | test | `convert_multiarith_item` |
| aqua | hf | test | `convert_aqua_item` |
| humaneval | hf | test | `convert_humaneval_item` |
| mbpp | hf | test | `convert_mbpp_item` |

## Offline Import Mode

- Single dataset command: `conda run -n lmas-trgc python scripts/prepare_public_datasets.py --dataset gsm8k --input-path /path/to/gsm8k.jsonl --overwrite`
- Directory command: `conda run -n lmas-trgc python scripts/prepare_public_datasets.py --dataset all --input-dir /path/to/raw_public --overwrite`
- Offline imports convert raw JSON/JSONL rows into standardized `TaskRecord` JSONL files.

## Optional HuggingFace Download Mode

- Explicit command: `conda run -n lmas-trgc python scripts/prepare_public_datasets.py --dataset gsm8k --allow-download --overwrite`
- Downloads are disabled unless `--allow-download` is present.
- `prontoqa`, `svamp`, and `multiarith` remain local JSONL sources in this step.

## Tests

- Command: `conda run -n lmas-trgc python -m pytest -q`
- Status: passed, `66 passed in 1.31s`.

## Script Checks

- Default public preparation: `conda run -n lmas-trgc python scripts/prepare_public_datasets.py --dataset all`
- Result: all 9 public datasets reported missing with `no_input_and_download_disabled`; no download was attempted.
- Synthetic generation: 16 Constraint MiniSet tasks and 16 Local-MAS Safety Set tasks.
- Manifest generation: 32 synthetic tasks, with all 9 public datasets recorded as missing.

## Git Commit

- Commit message: `feat: add public dataset preparation layer`
- commit hash is reported in final execution summary
