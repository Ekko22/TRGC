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

Copy the variable names from `.env.example` into your local `.env` or shell environment and fill in real values there. Do not commit `.env` or any API key. Model configuration is read through environment variable names in `configs/models.example.yaml`.

## Design Boundary

LMAS-TRGC does not add automatic recovery, automatic repair, automatic regeneration, learned routing, GNN risk classification, RL gate policy, or risk classifier training. Block, downweight, and selective verification are communication-layer gate actions, not recovery mechanisms.

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

## Later Development

Later stages will add task manifests, dataset preparation, agent runtime orchestration, attack payload implementations, real model configuration, SV service integration, G-Safeguard adapter integration, experiment execution, aggregation, tables, and figures.
