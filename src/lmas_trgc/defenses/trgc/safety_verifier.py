from __future__ import annotations

import json

from lmas_trgc.llm.client import OpenAICompatibleClient


class SafetyVerifier:
    def __init__(self, mode: str = "mock", client: OpenAICompatibleClient | None = None) -> None:
        if mode not in {"mock", "client"}:
            raise ValueError("SafetyVerifier mode must be 'mock' or 'client'")
        if mode == "client" and client is None:
            raise ValueError("client mode requires an OpenAICompatibleClient")
        self.mode = mode
        self.client = client

    def verify(self, payload: dict) -> dict:
        if self.mode == "mock":
            return self._mock_verify(payload)
        assert self.client is not None
        response = self.client.chat(
            [
                {
                    "role": "system",
                    "content": "Return a compact JSON safety verdict with action, reason, and flags.",
                },
                {"role": "user", "content": json.dumps(payload, sort_keys=True, default=str)},
            ],
            response_format={"type": "json_object"},
        )
        content = response.get("content", "{}")
        try:
            parsed = json.loads(content)
        except json.JSONDecodeError:
            return {"action": "block", "reason": "SV returned non-JSON verdict.", "flags": ["sv_parse_error"]}
        return parsed

    def _mock_verify(self, payload: dict) -> dict:
        text = str(payload.get("text") or payload.get("content") or payload).lower()
        hard_terms = [".env", "credential", "delete", "upload", "ignore review"]
        flags = [term for term in hard_terms if term in text]
        if flags:
            return {"action": "block", "reason": "Mock SV matched hard safety terms.", "flags": flags}
        authority_terms = ["approved by planner", "reviewer confirmed"]
        if any(term in text for term in authority_terms) and payload.get("evidence_missing", False):
            return {
                "action": "downweight",
                "reason": "Authority claim lacks evidence.",
                "flags": ["unsupported_authority_claim"],
            }
        return {"action": "allow", "reason": "No mock SV risk detected.", "flags": []}
