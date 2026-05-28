from lmas_trgc.agents.agent_runtime import AgentRuntime
from lmas_trgc.agents.prompt_builder import PromptBuilder
from lmas_trgc.agents.roles import AgentProfile
from lmas_trgc.llm.mock_client import MockLLMClient
from lmas_trgc.tasks.anchors import build_task_packet
from lmas_trgc.tasks.local_synthetic import generate_local_mas_safety_set


def test_agent_runtime_records_llm_usage_metadata():
    sender = AgentProfile(agent_id="A1", role_name="Planner", model_slot="M1")
    receiver = AgentProfile(agent_id="A2", role_name="ConstraintFactExtractor", model_slot="M1")
    runtime = AgentRuntime(agent_profile=sender, llm_client=MockLLMClient(), prompt_builder=PromptBuilder())
    message = runtime.generate_message(
        task_packet=build_task_packet(generate_local_mas_safety_set(1)[0]),
        receiver_profile=receiver,
        message_type="TASK_ASSIGNMENT",
        rendered_context="",
        round_id=1,
        parent_message_id=None,
    )
    usage = message.metadata["llm_usage"]
    assert usage["total_tokens"] > 0
    assert usage["call_count"] == 1
    assert "raw_response" not in message.metadata
