# DeepSeek Single-Model Real Smoke Infrastructure

## Date Time

2026-05-28 Asia/Shanghai

## Completed Work

- Added LLM usage records and aggregation helpers.
- Added LLM factory helpers for OpenAI-compatible task clients, DeepSeek M1, single-model agent mapping, and SV construction.
- Added LLM usage metadata to `AgentRuntime` messages.
- Added LLM call and token totals to `SingleRunResult`, message events, run summaries, metrics, and artifacts.
- Added `scripts/run_stage_c_deepseek_smoke.py` with dry-run, config-only, and explicit real-call modes.
- Added tests for usage aggregation, client factory safety, runtime usage metadata, single-run usage totals, and DeepSeek smoke guardrails.

## Design Boundaries

- Tests and default script execution do not call real LLMs.
- DeepSeek calls require explicit `--confirm-real-llm`.
- The real smoke maps A1-A7 to M1 / DeepSeek without changing agent configuration files.
- SV remains outside task topology and defaults to mock mode.
- No datasets are downloaded.
- No API keys, full prompts, final output text, final context text, or raw LLM responses are printed or committed.

## DeepSeek Single-Model Mode

`build_deepseek_client_from_registry` builds the M1 OpenAI-compatible client from the model registry. `build_single_model_agent_clients` maps the same M1 client to A1-A7 for a minimal real end-to-end smoke.

## Usage Tracking

Each agent message records:

- source model
- input tokens
- output tokens
- total tokens
- call count

Run summaries and metrics aggregate these fields across the run.

## Smoke Runner

The smoke runner supports:

- `--dry-run`
- `--check-config-only`
- `--confirm-real-llm`
- `--max-steps 2`
- `--sv-mode mock`
- optional artifact writing with judge and standard metrics

## Safety Guardrails

Without `--confirm-real-llm`, the script refuses to call DeepSeek and exits with code `2`. Config-only mode checks M1 and optional SV configuration without calling `/models` or `/chat/completions`.

## Tests

- Command: `conda run -n lmas-trgc python -m pytest -q`
- Status: passed, `159 passed in 11.27s`.

## Real Smoke Result

Real smoke was not executed because DeepSeek credentials were unavailable. Config-only reported missing `M1 api_key`.

## Git Commit

- Commit message: `feat: add deepseek single-model real smoke runner`
- Commit hash is reported in final execution summary.
