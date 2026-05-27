# Model Configuration and Client Infrastructure

## Date Time

2026-05-27 Asia/Shanghai

## Completed Work

- Added project path discovery, config file loading, secret redaction, and optional `.env` loading.
- Added a model registry for task model slots M1/M2/M3/M4 and the SV sidecar.
- Updated OpenAI-compatible client infrastructure with typed `LLMResponse`, runtime key checks, `/models` listing, and JSON response-format fallback.
- Updated `MockLLMClient` to match the production client interface without network calls.
- Updated token estimation utilities to use character-length estimates without `tiktoken`.
- Updated `SafetyVerifier` with structured `SafetyVerdict` output and mock/client modes.
- Added `scripts/check_model_endpoints.py` for no-network default config audits and optional `/models` checks.
- Added tests for config helpers, registry, LLM clients, and SV behavior.

## Design Boundaries

- No real `/chat/completions` calls are made in this step.
- No datasets are downloaded.
- No API key values are printed or committed.
- SV remains a trusted sidecar, not a task agent and not a topology node.
- This step does not implement recovery, repair, regeneration, learned routing, risk classifier training, or fake G-Safeguard results.

## Files Changed

- `src/lmas_trgc/core/config.py`
- `src/lmas_trgc/llm/client.py`
- `src/lmas_trgc/llm/mock_client.py`
- `src/lmas_trgc/llm/token_counter.py`
- `src/lmas_trgc/llm/registry.py`
- `src/lmas_trgc/defenses/trgc/safety_verifier.py`
- `src/lmas_trgc/defenses/trgc/controller.py`
- `src/lmas_trgc/defenses/full_checking.py`
- `scripts/check_model_endpoints.py`
- `tests/test_config.py`
- `tests/test_model_registry.py`
- `tests/test_llm_client.py`
- `tests/test_safety_verifier.py`
- `README.md`

## Test Result

- Command: `conda run -n lmas-trgc python -m pytest -q`
- Status: passed, `33 passed in 0.76s`.

## Endpoint Check Result

- Command: `conda run -n lmas-trgc python scripts/check_model_endpoints.py`
- Default behavior: configuration audit only; no network calls and no chat completions.
- Status: passed with exit code 0.
- Summary: M1 and SV have default base URLs; M2/M3/M4 base URLs are unset; all API keys are unset; no endpoints were checked by default.

## Git Commit

- Commit message: `feat: add model registry and LLM client infrastructure`
- Commit hash is reported in final execution summary.
