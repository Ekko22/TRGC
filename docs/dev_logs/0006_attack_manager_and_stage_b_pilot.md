# Attack Manager and Stage-B Pilot

## Date time

2026-05-28 Asia/Shanghai

## Completed Work

- Added final attack models for attack decisions and attack results.
- Added communication-layer targeting rules for high-value receivers, chain middle edges, graph direct-to-finalizer edges, and tree branch summary edges.
- Added domain-aware attack payload templates for Message Poisoning, Role Impersonation, and Relay Injection.
- Implemented MessagePoisoningAttack, RoleImpersonationAttack, RelayInjectionAttack, and AttackManager.
- Integrated AttackManager into SingleRunExecutor before MessageRouter delivery.
- Added Stage-B pilot runner for mock-only attack injection.
- Added tests for templates, attack manager behavior, single-run attack integration, and Stage-B script execution.

## Design Boundaries

- Attacks are communication-layer transformations, not agents.
- Attacks do not enter topology or protocol.
- Attacks do not modify `TransportEnvelope.actual_sender`.
- Attacks do not modify SV, topology, protocol, router internals, or prompt building.
- No real LLM calls, `/chat/completions`, `/models`, network access, or dataset downloads are made.
- BLOCK handling must not deliver injected attack content to receiver context.

## Attack Layer

The runtime sequence is:

1. `AgentRuntime` generates an `AgentMessage`.
2. `AttackManager` optionally transforms the message using route metadata and task packet anchors.
3. `MessageRouter` routes the original or attacked message.
4. `DefenseAdapter` performs pre-delivery gating.
5. Receiver context is updated according to the gate decision.

## Attack Strategies

- Message Poisoning appends a short injected communication update to selected high-value edges.
- Role Impersonation appends an authority-claim update and sets `declared_authority`.
- Relay Injection marks messages as forwarded and appends a forwarded upstream instruction.

Payloads are short, non-executable, and do not contain shell command strings.

## SingleRun Integration

`SingleRunExecutor` accepts an optional `AttackManager`. It builds preliminary route metadata, calls `AttackManager.apply_attack_if_needed(...)` after message generation and before `MessageRouter.route(...)`, and passes the attacked or original message into the router. Message events record whether an attack was injected, the attack type, changed fields, and route metadata including step and exposure fields. Results include `attacked_messages`.

## Stage-B Pilot Runner

`scripts/run_stage_b_pilot.py` runs synthetic-task, mock-only pilots for `none`, `message_poisoning`, `role_impersonation`, and `relay_injection`.

Smoke results:

- Graph + Message Poisoning + TRGC: completed, 13 total messages, 4 attacked.
- Graph + Role Impersonation + TRGC: completed, 13 total messages, 4 attacked.
- Graph + Relay Injection + TRGC: completed, 13 total messages, 12 attacked.
- Star + Message Poisoning + TRGC: completed, 11 total messages, 5 attacked.
- Chain + Message Poisoning + TRGC: completed, 6 total messages, 2 attacked.
- Tree + Relay Injection + TRGC: completed, 11 total messages, 10 attacked.

## Tests

- Command: `conda run -n lmas-trgc python -m pytest -q`
- Status: superseded by Step 6 repair validation in `0007_step6_attack_integration_fix.md`.

## Git Commit

- Commit message: `feat: add communication attack manager and stage-b pilot`
- commit hash is reported in final execution summary
