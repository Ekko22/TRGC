from lmas_trgc.llm.mock_client import MockLLMClient
from lmas_trgc.llm.usage import make_usage_record, merge_usage_records


def test_make_usage_record_from_mock_response():
    response = MockLLMClient(model_name="mock-a").chat([{"role": "user", "content": "hello"}])
    record = make_usage_record("A1", "mock-a", response)
    assert record.agent_id == "A1"
    assert record.call_count == 1
    assert record.total_tokens > 0


def test_merge_usage_records_by_agent_and_model():
    first = make_usage_record("A1", "mock-a", MockLLMClient(model_name="mock-a").chat([{"role": "user", "content": "a"}]))
    second = make_usage_record("A1", "mock-a", MockLLMClient(model_name="mock-a").chat([{"role": "user", "content": "b"}]))
    summary = merge_usage_records([first, second])
    assert summary.total_llm_calls == 2
    assert summary.by_agent["A1"].call_count == 2
    assert summary.by_model["mock-a"].call_count == 2


def test_merge_empty_usage_records():
    summary = merge_usage_records([])
    assert summary.total_llm_calls == 0
    assert summary.total_tokens == 0
