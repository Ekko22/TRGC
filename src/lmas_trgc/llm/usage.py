from __future__ import annotations

from pydantic import BaseModel, Field

from lmas_trgc.llm.client import LLMResponse


class LLMUsageRecord(BaseModel):
    agent_id: str | None = None
    model_name: str | None = None
    input_tokens: int = Field(default=0, ge=0)
    output_tokens: int = Field(default=0, ge=0)
    total_tokens: int = Field(default=0, ge=0)
    call_count: int = Field(default=0, ge=0)
    metadata: dict = Field(default_factory=dict)


class LLMUsageSummary(BaseModel):
    total_input_tokens: int = 0
    total_output_tokens: int = 0
    total_tokens: int = 0
    total_llm_calls: int = 0
    by_agent: dict[str, LLMUsageRecord] = Field(default_factory=dict)
    by_model: dict[str, LLMUsageRecord] = Field(default_factory=dict)


def make_usage_record(agent_id: str, model_name: str, response: LLMResponse) -> LLMUsageRecord:
    input_tokens = response.input_tokens or 0
    output_tokens = response.output_tokens or 0
    total_tokens = response.total_tokens if response.total_tokens is not None else input_tokens + output_tokens
    return LLMUsageRecord(
        agent_id=agent_id,
        model_name=model_name,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        total_tokens=total_tokens,
        call_count=1,
    )


def _add_usage(target: LLMUsageRecord, record: LLMUsageRecord) -> None:
    target.input_tokens += record.input_tokens
    target.output_tokens += record.output_tokens
    target.total_tokens += record.total_tokens
    target.call_count += record.call_count


def merge_usage_records(records: list[LLMUsageRecord]) -> LLMUsageSummary:
    summary = LLMUsageSummary()
    for record in records:
        agent_key = record.agent_id or "__unknown__"
        model_key = record.model_name or "__unknown__"
        summary.total_input_tokens += record.input_tokens
        summary.total_output_tokens += record.output_tokens
        summary.total_tokens += record.total_tokens
        summary.total_llm_calls += record.call_count
        if agent_key not in summary.by_agent:
            summary.by_agent[agent_key] = LLMUsageRecord(agent_id=agent_key)
        if model_key not in summary.by_model:
            summary.by_model[model_key] = LLMUsageRecord(model_name=model_key)
        _add_usage(summary.by_agent[agent_key], record)
        _add_usage(summary.by_model[model_key], record)
    return summary
