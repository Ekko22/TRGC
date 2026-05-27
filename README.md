# LMAS-TRGC

LMAS-TRGC is a reproducible experiment runtime for studying LLM-based multi-agent systems under communication attacks. It focuses on how communication topology changes collaboration quality, attack vulnerability, and robustness recovery under lightweight communication-layer defenses.

This project is not a general MAS SDK, web service, plugin platform, database system, or reimplementation of AutoGen, LangChain, or LangGraph. Its scope is the paper experiment runtime for controlled, interpretable LMAS-TRGC studies.

## Experiment Setting

The final experiment setting uses:

- 7 task agents.
- 1 trusted Safety Verifier sidecar.
- 4 communication topologies: Star, Chain, Graph, Tree.
- 4 attack conditions: No Attack, Message Poisoning, Role Impersonation, Relay Injection.
- 5 defenses: No Defense, Simple Content Guardrail, Full Checking-Light, G-Safeguard, TRGC.

TRGC is fixed as a communication-layer, lightweight, topology-aware, no-retraining, selective-verification, pre-delivery gating defense.

## Agents

The seven task agents are:

- A1 Planner.
- A2 ConstraintFactExtractor.
- A3 WorkerA.
- A4 WorkerB.
- A5 CriticTester.
- A6 DomainReviewer.
- A7 FinalizerExecutor.

The SV sidecar is `SV TrustedSafetyVerifier`. It is not a task agent, does not appear in topology nodes or edges, and is only called by TRGC or Full Checking-Light.

## Environment

This project uses one Conda environment: `lmas-trgc`.

Create or update the final Conda environment:

```bash
conda env create -f environment.yml
```

If the environment already exists:

```bash
conda env update -n lmas-trgc -f environment.yml --prune
```

Run tests only inside the project environment:

```bash
conda run -n lmas-trgc python -m pytest -q
```

## API Configuration

Copy the variable names from `.env.example` into your local `.env` or shell environment and fill in real values there:

```bash
cp .env.example .env
```

Do not commit `.env` or any API key. Task models are configured through `configs/models.example.yaml` and environment variables. The SV is a local lightweight OpenAI-compatible model endpoint, is not part of task topology, and only receives short verification payloads from TRGC or Full Checking-Light.

Check model configuration without network access:

```bash
conda run -n lmas-trgc python scripts/check_model_endpoints.py
```

Optionally check `/models` endpoints only:

```bash
conda run -n lmas-trgc python scripts/check_model_endpoints.py --check-models-endpoint
```

The endpoint check script never calls chat completions by default or with `--check-models-endpoint`; it only checks configuration unless `/models` probing is explicitly requested.

## Design Boundary

LMAS-TRGC does not add automatic recovery, automatic repair, automatic regeneration, learned routing, GNN risk classification, RL gate policy, or risk classifier training. Block, downweight, and selective verification are communication-layer gate actions, not recovery mechanisms.

## Task Data Layer

The main experiment uses 11 data sources:

- Public datasets: GSM8K, ProntoQA, MMLU, CSQA, SVAMP, MultiArith, AQuA, HumanEval, MBPP.
- Synthetic local datasets: Constraint MiniSet and Local-MAS Safety Set.

Step 3 does not automatically download public datasets. Public data may be added later as local JSONL files under `data/processed/public/`, but `data/raw/`, `data/processed/`, and `data/manifests/` must not be committed to Git.

Prepare a single public dataset from a local raw JSON/JSONL file:

```bash
conda run -n lmas-trgc python scripts/prepare_public_datasets.py --dataset gsm8k --input-path /path/to/gsm8k.jsonl --overwrite
```

Batch import public datasets from a local directory:

```bash
conda run -n lmas-trgc python scripts/prepare_public_datasets.py --dataset all --input-dir /path/to/raw_public --overwrite
```

Explicitly allow HuggingFace download for supported HF datasets:

```bash
conda run -n lmas-trgc python scripts/prepare_public_datasets.py --dataset gsm8k --allow-download --overwrite
```

Downloads are disabled by default. `prontoqa`, `svamp`, and `multiarith` are treated as `local_jsonl` sources by default and are not automatically downloaded from HuggingFace. Standardized public outputs are written under `data/processed/public/`, which must not be committed.

The synthetic datasets can be generated locally:

```bash
conda run -n lmas-trgc python scripts/create_synthetic_tasks.py --overwrite
```

The main task manifest can be built with:

```bash
conda run -n lmas-trgc python scripts/build_task_manifest.py
```

The final main experiment target is 104 tasks: 8 from each of the 9 public datasets, 16 from Constraint MiniSet, and 16 from Local-MAS Safety Set. When public datasets are not present locally, the manifest builder records them as missing and still creates a synthetic-only manifest for local smoke testing. Local-MAS Safety Set describes generic local multi-agent system scenarios and is not bound to any specific local agent product.

After public data preparation, rebuild the manifest:

```bash
conda run -n lmas-trgc python scripts/build_task_manifest.py
```

If all public and synthetic datasets are present, the manifest should reach 104 tasks.

## Step 1 Status

Step 1 initializes the runtime foundation:

- Final `src/lmas_trgc` package layout.
- Conda environment specification.
- Experiment configuration files.
- Core enums, IDs, config loading, message and envelope schemas.
- NetworkX topology manager and exposure estimator.
- Mock LLM client and OpenAI-compatible client boundary.
- No Defense, Simple Content Guardrail, Full Checking-Light, G-Safeguard boundary, and TRGC adapters.
- CSV loggers, script entry points, and unit tests.

Step 2 adds:

- Project path discovery and safer config loading.
- Secret redaction helpers and optional `.env` loading.
- Model registry for M1/M2/M3/M4 and the SV sidecar.
- OpenAI-compatible client infrastructure and mock client parity.
- Structured SV verdict parsing for mock and client modes.
- Model endpoint configuration audit script.

Step 3 adds:

- Standard task schema, anchors, task packets, and manifest entries.
- Fixed dataset registry for 9 public and 2 synthetic data sources.
- Local JSONL loader and HuggingFace loader stub with downloads disabled.
- Deterministic synthetic task generation and main manifest creation.
- Deterministic sampling and manifest validation tests.

Step 4 adds:

- Public dataset normalizers and converters for the 9 public datasets.
- Offline-first public dataset import from local JSON/JSONL.
- Optional explicit HuggingFace download mode for supported HF sources.
- Public processed JSONL integration with manifest building.

## Later Development

Later stages will add task manifests, dataset preparation, agent runtime orchestration, attack payload implementations, real model configuration, SV service integration, G-Safeguard adapter integration, experiment execution, aggregation, tables, and figures.
