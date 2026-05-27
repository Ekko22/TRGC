from lmas_trgc.agents.agent_runtime import AgentRuntime
from lmas_trgc.agents.prompt_builder import PromptBuilder
from lmas_trgc.agents.roles import AgentProfile
from lmas_trgc.llm.mock_client import MockLLMClient
from lmas_trgc.tasks.anchors import build_task_packet
from lmas_trgc.tasks.local_synthetic import generate_constraint_miniset


def test_agent_runtime_generates_agent_message_with_mock_client():
    packet = build_task_packet(generate_constraint_miniset(1)[0])
    sender = AgentProfile(agent_id="A1", role_name="Planner", model_slot="M3")
    receiver = AgentProfile(agent_id="A2", role_name="ConstraintFactExtractor", model_slot="M1")
    runtime = AgentRuntime(sender, MockLLMClient(), PromptBuilder())
    message = runtime.generate_message(
        task_packet=packet,
        receiver_profile=receiver,
        message_type="TASK_ASSIGNMENT",
        rendered_context="## Trusted messages\n(none)",
        round_id=1,
        parent_message_id="parent_msg",
        protocol_purpose="assign",
    )
    assert message.sender == "A1"
    assert message.receiver == "A2"
    assert message.sender_role == "Planner"
    assert message.receiver_role == "ConstraintFactExtractor"
    assert message.task_id == packet.task.task_id
    assert message.message_type == "TASK_ASSIGNMENT"
    assert message.is_forwarded is True
