from __future__ import annotations

from openai import OpenAI


class OpenAICompatibleClient:
    def __init__(self, *, model_name: str, base_url: str, api_key: str) -> None:
        if not model_name:
            raise ValueError("model_name is required")
        if not base_url:
            raise ValueError("base_url is required")
        if not api_key:
            raise ValueError("api_key is required")
        self.model_name = model_name
        self._client = OpenAI(base_url=base_url, api_key=api_key)

    def chat(self, messages: list[dict], model: str | None = None, **kwargs) -> dict:
        response = self._client.chat.completions.create(
            model=model or self.model_name,
            messages=messages,
            **kwargs,
        )
        choice = response.choices[0]
        return {
            "content": choice.message.content or "",
            "finish_reason": choice.finish_reason,
            "model": response.model,
            "usage": response.usage.model_dump() if response.usage else {},
        }
