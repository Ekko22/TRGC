from lmas_trgc.agents.prompt_builder import PromptBuilder
from lmas_trgc.agents.roles import AgentProfile
from lmas_trgc.tasks.anchors import build_task_packet
from lmas_trgc.tasks.local_synthetic import generate_local_mas_safety_set


def test_system_prompts_for_key_roles():
    builder = PromptBuilder()
    planner = builder.build_system_prompt(AgentProfile(agent_id="A1", role_name="Planner", model_slot="M3"))
    finalizer = builder.build_system_prompt(AgentProfile(agent_id="A7", role_name="FinalizerExecutor", model_slot="M3"))
    assert "Coordinate" in planner or "constraints" in planner
    assert "final" in finalizer.lower()


def test_user_prompt_contains_contract_fields_and_no_secrets():
    packet = build_task_packet(generate_local_mas_safety_set(1)[0])
    profile = AgentProfile(agent_id="A1", role_name="Planner", model_slot="M3")
    prompt = PromptBuilder().build_user_prompt(packet, profile, "## Trusted messages\n(none)", "plan")
    assert packet.task.task_id in prompt
    assert packet.task.dataset in prompt
    assert packet.answer_contract["metric"] in prompt
    assert "API key" not in prompt
    assert "LOCAL_SV_API_KEY" not in prompt
    assert "DEEPSEEK_API_KEY" not in prompt


def test_build_messages_returns_system_and_user():
    packet = build_task_packet(generate_local_mas_safety_set(1)[0])
    profile = AgentProfile(agent_id="A1", role_name="Planner", model_slot="M3")
    messages = PromptBuilder().build_messages(packet, profile, "(none)")
    assert [message["role"] for message in messages] == ["system", "user"]
