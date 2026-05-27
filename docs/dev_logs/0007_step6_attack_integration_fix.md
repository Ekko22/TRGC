# Step 6 Attack Integration Fix

## Date time

2026-05-28 Asia/Shanghai

## Problem Found

- Stage-B script expected attack manager integration.
- SingleRunExecutor did not yet fully pass messages through AttackManager with complete route metadata.
- Result models needed explicit attack tracking fields for validation and JSON summaries.

## Root Cause

The communication attack layer and Stage-B script were present, but the single-run execution path needed a tighter contract: attack execution had to occur after `AgentRuntime.generate_message(...)` and before `MessageRouter.route(...)`, with the effective attack status carried into routing and result events.

## Fix Implemented

- Added and verified the `attack_manager` parameter on `SingleRunExecutor`.
- Ensured `AttackManager.apply_attack_if_needed(...)` is called before `MessageRouter.route(...)`.
- Passed the attacked message to the router when an attack is injected.
- Passed `injected_by_attack=True` and the effective attack type only for actually attacked messages.
- Added `MessageEvent` attack fields: `attack_injected`, `attack_type`, and `attack_changed_fields`.
- Added `SingleRunResult.attacked_messages`.
- Expanded preliminary route metadata with `step_id`, `message_type`, and `exposure_level`.
- Added regression coverage for `attack_type="none"` and route metadata fields.
- Stage-B smoke now reports `attacked_messages > 0` for all three implemented attack types.

## Validation

- Graph + Message Poisoning + TRGC: completed and reports attacked messages.
- Graph + Role Impersonation + TRGC: completed and reports attacked messages.
- Graph + Relay Injection + TRGC: completed and reports attacked messages.
- Star, Chain, Graph, and Tree topology smoke checks completed with injected attacks.

## Tests

- Command: `conda run -n lmas-trgc python -m pytest -q`
- Status: passed, `95 passed in 3.18s`.

## Git Commit

- Commit message: `fix: integrate attack manager into single-run executor`
- commit hash is reported in final execution summary
