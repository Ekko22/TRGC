from __future__ import annotations

from lmas_trgc.llm.token_counter import estimate_tokens


class MockLLMClient:
    def chat(self, messages: list[dict], model: str | None = None, **kwargs) -> dict:
        joined = "\n".join(str(message.get("content", "")) for message in messages)
        content = "Mock response for LMAS-TRGC runtime foundation."
        return {
            "content": content,
            "model": model or "mock-model",
            "input_tokens": estimate_tokens(joined),
            "output_tokens": estimate_tokens(content),
            "finish_reason": "stop",
        }
