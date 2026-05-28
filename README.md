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

When `--judge-mode` is provided, saved artifacts also include `judge_outcome.json` and `standard_metrics.json`. These files store structured judge outcomes and standard effect metrics only; they do not store final output text.

## Stage-B Batch Runs

Step 8 adds a manifest-backed Stage-B batch runner, batch artifact index, and aggregate metrics. Single-run smoke still uses `run_stage_b_pilot.py`; batch execution uses `run_stage_b_batch.py`.

The default batch is synthetic and mock-only. It does not call real LLMs, `/chat/completions`, `/models`, or external services. Batch outputs are written under `results/runs/stage_b_batches/<batch_id>/`, while each individual run artifact remains under `results/runs/stage_b/<run_id>/`. Both paths must stay out of Git.

Batch and pilot runners support run-level parallelism with `--max-workers`. A single run's 7-agent protocol is still strictly serial: agent steps, message propagation, attack injection, TRGC gates, and final context accumulation are not parallelized inside `SingleRunExecutor`. Only independent runs are scheduled concurrently.

The tqdm progress bar is enabled by default and writes to stderr, so `--json` keeps stdout as clean JSON. Use `--no-progress` to disable it. Stage-B mock batches can use higher worker counts such as 4 or 8. Real Stage-C DeepSeek pilots should start with `--max-workers 2` to reduce API rate-limit pressure.

Dry-run the default batch:

```bash
conda run -n lmas-trgc python scripts/run_stage_b_batch.py --dry-run --json
```

Run the default batch:

```bash
conda run -n lmas-trgc python scripts/run_stage_b_batch.py --judge-mode mock_protocol --json
```

Run a wider Stage-B matrix:

```bash
conda run -n lmas-trgc python scripts/run_stage_b_batch.py --datasets local_mas_safety,constraint_miniset --task-limit-per-dataset 2 --topologies star,chain,graph,tree --attacks message_poisoning,role_impersonation,relay_injection --defenses no_defense,trgc --json
```

Run a Stage-B mock batch in parallel:

```bash
conda run -n lmas-trgc python scripts/run_stage_b_batch.py --max-workers 4 --json
```

Disable the progress bar:

```bash
conda run -n lmas-trgc python scripts/run_stage_b_batch.py --max-workers 4 --no-progress --json
```

Aggregate an existing batch:

```bash
conda run -n lmas-trgc python scripts/aggregate_stage_b_artifacts.py --batch-dir results/runs/stage_b_batches/<batch_id> --group-by topology --group-by defense_name --json
```

Aggregate standard effect metrics:

```bash
conda run -n lmas-trgc python scripts/aggregate_standard_metrics.py --batch-dir results/runs/stage_b_batches/<batch_id> --group-by topology --group-by defense_name --json
```

## Judge and Standard Effect Metrics

Step 9 adds a non-LLM judge layer and standard effect metrics for later paper tables.

Judge modes:

- `mock_protocol`: engineering validation for mock-only runs. It is marked `valid_for_paper=false` and must not be used as a formal paper result.
- `rule_based`: deterministic rule-based scoring for future real LLM outputs.

Standard metrics:

- Clean TSR / Accuracy: task success under `attack_type=none`.
- Robust TSR: task success under attack.
- ASR: attack success rate under attack.
- SVR: safety violation rate.
- Benign Drop: clean no-defense baseline minus clean defended TSR.

Current Stage-B batch defaults to `judge_mode=mock_protocol` and remains mock-only:

```bash
conda run -n lmas-trgc python scripts/run_stage_b_batch.py --judge-mode mock_protocol --json
```

## DeepSeek Single-Model Real Smoke

Step 10A adds an explicit opt-in DeepSeek-only real smoke runner. In this mode all seven task agents A1-A7 are mapped to M1 / DeepSeek at runtime; `configs/agents.yaml` is not modified. SV remains a sidecar and defaults to mock mode.

The script is safe by default:

- pytest never calls real LLMs.
- Dry-run and config-only modes never call real LLMs.
- A real DeepSeek call is refused unless `--confirm-real-llm` is provided.
- The recommended smoke is one synthetic task with `--max-steps 2`.
- Real smoke can incur API cost and is not a paper result.

Dry-run:

```bash
conda run -n lmas-trgc python scripts/run_stage_c_deepseek_smoke.py --dry-run --json
```

Configuration check:

```bash
conda run -n lmas-trgc python scripts/run_stage_c_deepseek_smoke.py --check-config-only --json
```

Real DeepSeek smoke:

```bash
conda run -n lmas-trgc python scripts/run_stage_c_deepseek_smoke.py --confirm-real-llm --topology graph --attack message_poisoning --defense trgc --dataset local_mas_safety --max-steps 2 --sv-mode mock --save-artifact --overwrite --json
```

The smoke validates the DeepSeek API path, 7-agent runtime, communication attack injection, TRGC pre-delivery checks, judge compatibility, artifact writing, and LLM token/call usage tracking. Later steps will extend this to local SV client mode and heterogeneous M1-M4 task models.

Step 10A real DeepSeek smoke was successfully executed with explicit `--confirm-real-llm`. The smoke used `max_steps=2`, graph topology, message poisoning, TRGC, and SV client mode. It validated the real DeepSeek task-model path, local SV client path, TRGC defense, artifact writing, judge, and usage tracking. This is an engineering validation run, not a paper result.

## DeepSeek Manifest Pilot

Step 12 adds an opt-in Stage-C manifest pilot over `main_v2_104`. It selects one task per active dataset by default, so the default pilot covers all 11 datasets, including ProntoQA, and runs 22 real-model runs:

- 11 selected tasks.
- Graph topology.
- Message Poisoning attack.
- No Defense and TRGC.
- DeepSeek M1 mapped to all A1-A7 task agents.
- SV client mode by default.
- `max_steps=3` to reach Graph direct-to-finalizer and other high-value attack edges.

This pilot is a real-data, real-DeepSeek engineering validation for the manifest, attack, defense, judge, artifact, and usage-tracking path. It is not the 8320-run main experiment and is not a paper result. It never calls a real LLM unless `--confirm-real-llm` is supplied.

Dry-run without network calls:

```bash
conda run -n lmas-trgc python scripts/run_stage_c_deepseek_manifest_pilot.py --dry-run --json
```

Configuration check without chat calls:

```bash
conda run -n lmas-trgc python scripts/run_stage_c_deepseek_manifest_pilot.py --check-config-only --json
```

Default real pilot:

```bash
conda run -n lmas-trgc python scripts/run_stage_c_deepseek_manifest_pilot.py --confirm-real-llm --overwrite --json
```

Parallel real pilot with the recommended low worker count:

```bash
conda run -n lmas-trgc python scripts/run_stage_c_deepseek_manifest_pilot.py --confirm-real-llm --max-workers 2 --overwrite --json
```

Optional mock SV fallback:

```bash
conda run -n lmas-trgc python scripts/run_stage_c_deepseek_manifest_pilot.py --confirm-real-llm --allow-sv-mock-fallback --overwrite --json
```

Aggregate a completed pilot batch:

```bash
conda run -n lmas-trgc python scripts/aggregate_stage_c_manifest_pilot.py --batch-dir results/runs/stage_c_manifest_batches/<batch_id> --group-by dataset --group-by defense_name --json
```

Step 12C runs a parallel DeepSeek manifest pilot over `main_v2_104`. The default clean pilot is:

- 11 datasets x 1 task x graph x message_poisoning x no_defense/trgc = 22 runs.
- Recommended real-LLM concurrency: `--max-workers 2`.
- Engineering pilot only; not a paper result.
- Results are stored under `results/runs/stage_c_manifest_batches/<batch_id>/` and are not committed.

```bash
conda run -n lmas-trgc python scripts/run_stage_c_deepseek_manifest_pilot.py --confirm-real-llm --batch-id stage_c_manifest_parallel_clean_22 --tasks-per-dataset 1 --topologies graph --attacks message_poisoning --defenses no_defense,trgc --max-steps 3 --max-workers 2 --sv-mode client --overwrite --json
```

## Task Data Layer

The main experiment uses 11 data sources:

- Public datasets: GSM8K, ProntoQA, MMLU, CSQA, SVAMP, MultiArith, AQuA, HumanEval, MBPP.
- Synthetic local datasets: Constraint MiniSet and Local-MAS Safety Set.

The complete main manifest requires 104 tasks: 8 from each public dataset and 16 from each synthetic dataset. Public datasets can be prepared either by explicit HuggingFace download or by importing local raw JSON/JSONL files. `data/raw/`, `data/processed/`, and `data/manifests/` must not be committed to Git.

Downloads are disabled by default. Prepare all supported public datasets with explicit download enabled:

```bash
conda run -n lmas-trgc python scripts/prepare_public_datasets.py --dataset all --allow-download --overwrite --json
```

If the default HuggingFace endpoint is unavailable, specify a mirror:

```bash
conda run -n lmas-trgc python scripts/prepare_public_datasets.py --dataset all --allow-download --hf-endpoint https://hf-mirror.com --overwrite --json
```

Import local raw public datasets from a directory:

```bash
conda run -n lmas-trgc python scripts/prepare_public_datasets.py --dataset all --input-dir data/raw/public --overwrite --json
```

Prepare a single public dataset from a local raw JSON/JSONL file:

```bash
conda run -n lmas-trgc python scripts/prepare_public_datasets.py --dataset gsm8k --input-path /path/to/gsm8k.jsonl --overwrite
```

Print accepted raw JSON/JSONL shapes before preparing local files:

```bash
conda run -n lmas-trgc python scripts/print_public_dataset_raw_schema.py --dataset all --json
```

`gsm8k`, `mmlu`, `csqa`, `aqua`, `humaneval`, and `mbpp` use configured HuggingFace candidates when `--allow-download` is supplied. `prontoqa`, `svamp`, and `multiarith` first look for local raw files under `data/raw/public/` and then try configured HuggingFace candidates. If a public dataset cannot be downloaded or imported, it remains missing or failed; synthetic data is never used as a substitute for public data. Standardized public outputs are written under `data/processed/public/`, which must not be committed.

The synthetic datasets can be generated locally:

```bash
conda run -n lmas-trgc python scripts/create_synthetic_tasks.py --overwrite
```

Audit dataset readiness:

```bash
conda run -n lmas-trgc python scripts/audit_dataset_readiness.py --json
```

Freeze the full main manifest:

```bash
conda run -n lmas-trgc python scripts/build_task_manifest.py --require-full --output data/manifests/main_manifest.json --json
```

Audit the finalized 104-task data package:

```bash
conda run -n lmas-trgc python scripts/audit_task_quality.py --require-full --json
```

The active quality-audited pool is `main_v2_104`: 9 public datasets, including ProntoQA, plus 2 synthetic datasets. The JSON quality report is written to `data/manifests/task_quality_report.json` and is not committed. The Markdown audit summary is written to `docs/dev_logs/0015_data_quality_audit.md` and intentionally omits full prompts, code bodies, and raw rows.

The final main experiment target is 104 tasks: 8 from each of the 9 active public datasets, 16 from Constraint MiniSet, and 16 from Local-MAS Safety Set. When public datasets are not present locally, the manifest builder records them as missing and can still create a synthetic-only manifest for engineering smoke tests. `--require-full` enforces the complete 104-task requirement and fails if any dataset is missing or short. Local-MAS Safety Set describes generic local multi-agent system scenarios and is not bound to any specific local agent product.

If automatic public download fails, place raw files at:

```bash
data/raw/public/<dataset>.jsonl
```

The readiness and manifest commands are intentionally strict: `audit_dataset_readiness.py --json` reports which datasets are ready, and `build_task_manifest.py --require-full` refuses to freeze a main manifest unless all 104 target tasks are available.

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
- Fixed dataset registry for 9 active public and 2 synthetic data sources.
- Local JSONL loader and HuggingFace loader stub with downloads disabled.
- Deterministic synthetic task generation and main manifest creation.
- Deterministic sampling and manifest validation tests.

Step 4 adds:

- Public dataset normalizers and converters for the active public datasets.
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

Step 8 adds:

- TaskResolver modes for synthetic, processed JSONL, and manifest-backed task selection.
- Stage-B batch runner over task, topology, attack, and defense matrices.
- Batch-level run index, summary, aggregate metrics, README, and manifest files.
- Pure-Python aggregation over saved Stage-B artifacts.

Step 9 adds:

- Rule-based and mock-protocol judge modes.
- Standard effect metrics for Clean TSR, Robust TSR, ASR, SVR, and Benign Drop.
- Optional judge outcome and standard metrics files in run artifacts.
- Batch-level standard effect metric aggregation.

Step 10A adds:

- DeepSeek-only real smoke runner with explicit `--confirm-real-llm` opt-in.
- Single-model client mapping for all task agents through M1.
- LLM call and token usage tracking in message events, summaries, metrics, and artifacts.
- Safe dry-run and config-only checks that do not call external APIs.
- Successful real DeepSeek + SV client smoke validation for the bounded `graph/message_poisoning/trgc/max_steps=2` path.

Step 11 adds:

- Dataset readiness auditing for all 11 active dataset sources.
- Explicit public dataset download/import reporting with missing and failed dataset states.
- Strict `--require-full` manifest freezing for the 104-task main pool.
- HuggingFace candidate fallback, mirror/cache configuration, and raw schema guidance for public datasets.

## Later Development

Later stages will add heterogeneous M1-M4 real model execution, dataset-backed pilot execution after the 104-task manifest is frozen, G-Safeguard adapter integration, main matrix execution, tables, and figures.
