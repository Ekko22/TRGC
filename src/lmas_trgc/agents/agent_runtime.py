from __future__ import annotations

from lmas_trgc.llm.mock_client import MockLLMClient


class AgentRuntime:
    def __init__(self, agent_id: str, role: str, client: MockLLMClient | None = None) -> None:
        self.agent_id = agent_id
        self.role = role
        self.client = client or MockLLMClient()

    def respond(self, prompt: str) -> dict:
        return self.client.chat([{"role": "user", "content": prompt}])
