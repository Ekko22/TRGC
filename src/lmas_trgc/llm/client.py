from __future__ import annotations

from typing import Any

from openai import BadRequestError, OpenAI
from pydantic import BaseModel


class LLMResponse(BaseModel):
    content: str
    model: str
    input_tokens: int | None = None
    output_tokens: int | None = None
    total_tokens: int | None = None
    raw_response: dict | None = None

    def __getitem__(self, key: str) -> Any:
        return getattr(self, key)


class OpenAICompatibleClient:
    def __init__(
        self,
        *,
        model_name: str,
        base_url: str,
        api_key: str | None,
        timeout: float = 60.0,
        max_retries: int = 2,
    ) -> None:
        if not model_name:
            raise ValueError("model_name is required")
        if not base_url:
            raise ValueError("base_url is required")
        self.model_name = model_name
        self.base_url = base_url
        self._api_key_set = bool(api_key)
        self._client = OpenAI(
            base_url=base_url,
            api_key=api_key or "missing-api-key",
            timeout=timeout,
            max_retries=max_retries,
        )

    def chat(
        self,
        messages: list[dict],
        temperature: float = 0,
        top_p: float = 1,
        max_tokens: int | None = None,
        response_format: str | None = None,
        extra_body: dict | None = None,
    ) -> LLMResponse:
        if not self._api_key_set:
            raise RuntimeError("API key is required before calling chat().")
        kwargs: dict[str, Any] = {
            "model": self.model_name,
            "messages": messages,
            "temperature": temperature,
            "top_p": top_p,
        }
        if max_tokens is not None:
            kwargs["max_tokens"] = max_tokens
        if response_format == "json":
            kwargs["response_format"] = {"type": "json_object"}
        if extra_body is not None:
            kwargs["extra_body"] = extra_body
        try:
            response = self._client.chat.completions.create(**kwargs)
        except BadRequestError as exc:
            message = str(exc).lower()
            if response_format == "json" and ("response_format" in message or "json_object" in message):
                kwargs.pop("response_format", None)
                response = self._client.chat.completions.create(**kwargs)
            else:
                raise
        choice = response.choices[0]
        usage = response.usage
        raw_response = response.model_dump() if hasattr(response, "model_dump") else None
        return LLMResponse(
            content=choice.message.content or "",
            model=response.model,
            input_tokens=usage.prompt_tokens if usage else None,
            output_tokens=usage.completion_tokens if usage else None,
            total_tokens=usage.total_tokens if usage else None,
            raw_response=raw_response,
        )

    def list_models(self) -> list[str]:
        if not self._api_key_set:
            raise RuntimeError("API key is required before calling list_models().")
        response = self._client.models.list()
        return [model.id for model in response.data]
