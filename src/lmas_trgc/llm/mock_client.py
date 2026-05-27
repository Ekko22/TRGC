from __future__ import annotations

from lmas_trgc.llm.client import LLMResponse
from lmas_trgc.llm.token_counter import estimate_tokens_from_messages, estimate_tokens_from_text


class MockLLMClient:
    def __init__(
        self,
        model_name: str = "mock-model",
        canned_response: str | None = None,
        invalid_json: bool = False,
    ) -> None:
        self.model_name = model_name
        self.canned_response = canned_response
        self.invalid_json = invalid_json

    def chat(
        self,
        messages: list[dict],
        temperature: float = 0,
        top_p: float = 1,
        max_tokens: int | None = None,
        response_format: str | None = None,
        extra_body: dict | None = None,
        model: str | None = None,
        **kwargs,
    ) -> LLMResponse:
        if self.canned_response is not None:
            content = self.canned_response
        elif response_format == "json" and not self.invalid_json:
            content = '{"verdict":"allow","reason":"mock","confidence":"high"}'
        elif response_format == "json" and self.invalid_json:
            content = "not valid json"
        else:
            content = "Mock response."
        input_tokens = estimate_tokens_from_messages(messages)
        output_tokens = estimate_tokens_from_text(content)
        return LLMResponse(
            content=content,
            model=model or self.model_name,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=input_tokens + output_tokens,
            raw_response={"mock": True},
        )

    def list_models(self) -> list[str]:
        return [self.model_name]
