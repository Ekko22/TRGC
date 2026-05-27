import json

import pytest

from lmas_trgc.llm.client import LLMResponse, OpenAICompatibleClient
from lmas_trgc.llm.mock_client import MockLLMClient


def test_mock_llm_chat_returns_response():
    client = MockLLMClient(model_name="mock-a")
    response = client.chat([{"role": "user", "content": "hello"}])
    assert isinstance(response, LLMResponse)
    assert response.content == "Mock response."
    assert response.input_tokens and response.input_tokens > 0
    assert response.output_tokens and response.output_tokens > 0


def test_mock_llm_json_response_is_valid_json():
    client = MockLLMClient()
    response = client.chat([{"role": "user", "content": "check"}], response_format="json")
    parsed = json.loads(response.content)
    assert parsed["verdict"] == "allow"


def test_mock_llm_list_models():
    client = MockLLMClient(model_name="mock-sv")
    assert client.list_models() == ["mock-sv"]


def test_openai_client_initialization_does_not_require_network():
    client = OpenAICompatibleClient(model_name="x", base_url="http://localhost:1/v1", api_key=None)
    assert client.model_name == "x"


def test_openai_client_without_key_blocks_runtime_calls():
    client = OpenAICompatibleClient(model_name="x", base_url="http://localhost:1/v1", api_key=None)
    with pytest.raises(RuntimeError):
        client.list_models()
    with pytest.raises(RuntimeError):
        client.chat([{"role": "user", "content": "hello"}])
