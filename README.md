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

## Runtime Protocol Layer

The runtime separates three concerns:

- Topology defines which directed communication edges are legal.
- Protocol defines the ordered message-passing steps for a single task run.
- Defense defines pre-delivery gating behavior for each routed message.

SV is not part of topology or protocol. It remains a sidecar that can only be called through TRGC or Full Checking-Light.

Stage-A smoke runs use `MockLLMClient` only. They do not call real LLMs, `/chat/completions`, `/models`, datasets, or external services.

Run one Stage-A smoke:

```bash
conda run -n lmas-trgc python scripts/run_stage_a_smoke.py --topology star --defense trgc --json
```

Run all four topology smoke checks:

```bash
conda run -n lmas-trgc python scripts/run_stage_a_smoke.py --topology star --defense trgc --json
conda run -n lmas-trgc python scripts/run_stage_a_smoke.py --topology chain --defense trgc --json
conda run -n lmas-trgc python scripts/run_stage_a_smoke.py --topology graph --defense trgc --json
conda run -n lmas-trgc python scripts/run_stage_a_smoke.py --topology tree --defense trgc --json
```

## Communication Attacks

Step 6 adds a communication-layer attack manager. Attacks are not agents, do not enter topology or protocol, and do not change the true transport sender recorded by the router. They occur after `AgentRuntime` generates an `AgentMessage` and before `MessageRouter` applies topology and defense checks.

`AttackManager` is integrated into `SingleRunExecutor`: each protocol message is generated first, optionally transformed by the active attack strategy, and then routed through `MessageRouter` with `injected_by_attack` and the effective attack type recorded in the transport envelope. Message events record `attack_injected`, `attack_type`, and `attack_changed_fields`; run summaries report `attacked_messages`.

Supported attacks:

- Message Poisoning.
- Role Impersonation.
- Relay Injection.

Stage-B pilot uses `MockLLMClient` only and does not call real LLMs or external services.

Run one Stage-B pilot:

```bash
conda run -n lmas-trgc python scripts/run_stage_b_pilot.py --topology graph --attack message_poisoning --defense trgc --json
```

Run the three attack smoke checks:

```bash
conda run -n lmas-trgc python scripts/run_stage_b_pilot.py --topology graph --attack message_poisoning --defense trgc --json
conda run -n lmas-trgc python scripts/run_stage_b_pilot.py --topology graph --attack role_impersonation --defense trgc --json
conda run -n lmas-trgc python scripts/run_stage_b_pilot.py --topology graph --attack relay_injection --defense trgc --json
```

## Stage-B Result Artifacts

By default, Stage-B prints a run summary and does not write files. Use `--save-artifact` to persist a structured run artifact under `results/runs/stage_b/<run_id>/`.

Each run artifact contains:

- `run_summary.json`
- `message_events.jsonl`
- `message_events.csv`
- `topology_events.jsonl`
- `metrics.json`
- `config_snapshot.json`
- `README.md`
- `manifest.json`

Run and save one Stage-B artifact:

```bash
conda run -n lmas-trgc python scripts/run_stage_b_pilot.py --topology graph --attack message_poisoning --defense trgc --save-artifact --json
```

Inspect and validate the artifact:

```bash
conda run -n lmas-trgc python scripts/inspect_run_artifact.py results/runs/stage_b/<run_id>
```

Artifacts store hashes, structured event fields, and metrics. They do not store full prompts, final context text, API keys, or raw LLM responses. `results/runs/` must not be committed to Git.

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

Step 5 adds:

- Explicit topology protocol definitions for Star, Chain, Graph, and Tree.
- Tree topology return edges for branch aggregation and finalization.
- Agent profiles, context buckets, prompt building, and mock-only agent runtime.
- SingleRunExecutor that routes every protocol message through MessageRouter and DefenseAdapter.
- Stage-A smoke runner for 7-agent mock execution.

Step 6 adds:

- AttackManager and independent communication attack strategies.
- Domain-aware attack payload templates for message poisoning, role impersonation, and relay injection.
- Attack targeting rules for high-value receivers, graph direct-to-finalizer edges, chain middle edges, and tree branch summaries.
- Stage-B pilot runner for mock-only attack injection smoke tests.

Step 7 adds:

- Structured Stage-B run artifacts under `results/runs/stage_b/<run_id>/`.
- Run summary, message event, topology event, metrics, config snapshot, README, and manifest files.
- Artifact writer and loader modules with validation.
- Optional Stage-B persistence via `--save-artifact`; default Stage-B runs remain stdout-only.

## Later Development

Later stages will add dataset-backed pilot execution, real model execution modes, SV service integration, G-Safeguard adapter integration, matrix execution, aggregation, tables, and figures.
