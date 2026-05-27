from __future__ import annotations

from lmas_trgc.agents.prompt_builder import PromptBuilder
from lmas_trgc.agents.roles import AgentProfile
from lmas_trgc.communication.message import AgentMessage
from lmas_trgc.core.ids import make_message_id
from lmas_trgc.llm.client import OpenAICompatibleClient
from lmas_trgc.llm.mock_client import MockLLMClient
from lmas_trgc.tasks.schema import TaskPacket


class AgentRuntime:
    def __init__(
        self,
        agent_profile: AgentProfile | None = None,
        llm_client: MockLLMClient | OpenAICompatibleClient | None = None,
        prompt_builder: PromptBuilder | None = None,
        agent_id: str | None = None,
        role: str | None = None,
        client: MockLLMClient | None = None,
    ) -> None:
        if agent_profile is None:
            if agent_id is None or role is None:
                raise ValueError("agent_profile or agent_id/role must be provided")
            agent_profile = AgentProfile(agent_id=agent_id, role_name=role, model_slot="mock")
        self.agent_profile = agent_profile
        self.client = llm_client or client or MockLLMClient()
        self.prompt_builder = prompt_builder or PromptBuilder()

    def respond(self, prompt: str) -> dict:
        return self.client.chat([{"role": "user", "content": prompt}])

    def generate_message(
        self,
        task_packet: TaskPacket,
        receiver_profile: AgentProfile,
        message_type: str,
        rendered_context: str,
        round_id: int,
        parent_message_id: str | None,
        protocol_purpose: str | None = None,
    ) -> AgentMessage:
        messages = self.prompt_builder.build_messages(
            task_packet=task_packet,
            agent_profile=self.agent_profile,
            rendered_context=rendered_context,
            protocol_purpose=protocol_purpose,
        )
        response = self.client.chat(messages)
        content = response.content
        message_id = make_message_id(
            task_id=task_packet.task.task_id,
            round_id=round_id,
            sender=self.agent_profile.agent_id,
            receiver=receiver_profile.agent_id,
            content=content,
        )
        return AgentMessage(
            message_id=message_id,
            parent_message_id=parent_message_id,
            round_id=round_id,
            sender=self.agent_profile.agent_id,
            receiver=receiver_profile.agent_id,
            sender_role=self.agent_profile.role_name,
            receiver_role=receiver_profile.role_name,
            message_type=message_type,
            content=content,
            reasoning_summary=None,
            confidence=None,
            task_id=task_packet.task.task_id,
            is_forwarded=parent_message_id is not None,
            declared_authority=None,
        )
