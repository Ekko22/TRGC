# Agent Protocol and Single-Run Runtime

## Date time

2026-05-28 Asia/Shanghai

## Completed Work

- Added explicit protocol definitions for Star, Chain, Graph, and Tree.
- Updated Tree topology with branch return and finalization edges.
- Added protocol validation against topology edges and MessageType enum values.
- Added task-agent profiles, context buckets, prompt building, and mock runtime message generation.
- Added defense factory for stable adapter creation.
- Added SingleRunExecutor that executes protocol edges through MessageRouter and DefenseAdapter.
- Updated Stage-A smoke script to run complete mock-only 7-agent flows.
- Added tests for protocols, prompt builder, agent runtime, single-run execution, and Stage-A smoke script.

## Design Boundaries

- No real LLM calls are made.
- No `/chat/completions` or `/models` calls are made.
- No external network access or dataset download is required.
- SV is excluded from topology and protocol and remains a sidecar for TRGC or Full Checking-Light.
- BLOCK handling writes only a safety notice to receiver context and does not deliver blocked message content.
- This step does not add recovery, repair, regeneration, attack injection, learned routing, risk classifier training, or fake G-Safeguard results.

## Topology Update

Tree topology now supports branch aggregation:

- Leaf-to-parent return: `A3 -> A2`, `A4 -> A2`, `A5 -> A6`.
- Branch-to-root return: `A2 -> A1`, `A6 -> A1`.
- Root-to-finalizer finalization: `A1 -> A7`.

SV does not appear in any topology nodes, critical nodes, or edges.

## Protocol Layer

`configs/protocols.yaml` defines ordered message-passing steps for each topology. `ProtocolManager` validates that every protocol edge is legal under `TopologyManager`, that step IDs are strictly increasing, and that message types map to `MessageType`.

## PromptBuilder and AgentRuntime

`PromptBuilder` creates role-specific system prompts and task-aware user prompts without exposing API keys, SV prompts, route metadata, or defense internals. `AgentRuntime` uses an injected client and does not read global config or network state.

## SingleRunExecutor

`SingleRunExecutor` executes a task packet over a selected topology protocol. Every message goes through `MessageRouter` and the selected `DefenseAdapter`. Completion means the protocol finished, not that the answer is correct.

## Stage-A Smoke Runner

Stage-A smoke runs use synthetic tasks and `MockLLMClient` only. The four topology smoke commands completed successfully with TRGC.

- Star: completed, 11 total messages, 11 delivered.
- Chain: completed, 6 total messages, 6 delivered.
- Graph: completed, 13 total messages, 13 delivered.
- Tree: completed, 11 total messages, 11 delivered.

## Tests

- Command: `conda run -n lmas-trgc python -m pytest -q`
- Status: passed, `78 passed in 2.26s`.

## Git Commit

- Commit message: `feat: add agent protocol and single-run runtime`
- commit hash is reported in final execution summary
