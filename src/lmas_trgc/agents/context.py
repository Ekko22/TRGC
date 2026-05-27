from __future__ import annotations

from lmas_trgc.communication.prompt_assembler import assemble_receiver_context

CONTEXT_BUCKETS = {"trusted", "warning", "untrusted", "safety_notice"}


class AgentContextStore:
    def __init__(self, agent_ids: list[str]) -> None:
        if "SV" in agent_ids:
            raise ValueError("SV must not have task-agent context")
        self.agent_ids = list(agent_ids)
        self._store: dict[str, dict[str, list[dict]]] = {}
        self.reset()

    def _assert_agent(self, agent_id: str) -> None:
        if agent_id not in self._store:
            raise KeyError(f"Unknown agent context: {agent_id}")

    def _assert_bucket(self, bucket: str) -> None:
        if bucket not in CONTEXT_BUCKETS:
            raise ValueError(f"Unknown context bucket: {bucket}")

    def add_message(self, agent_id: str, bucket: str, content: str, message_id: str) -> None:
        self._assert_agent(agent_id)
        self._assert_bucket(bucket)
        self._store[agent_id][bucket].append({"message_id": message_id, "content": content})

    def get_bucket(self, agent_id: str, bucket: str) -> list[dict]:
        self._assert_agent(agent_id)
        self._assert_bucket(bucket)
        return list(self._store[agent_id][bucket])

    def get_context(self, agent_id: str) -> dict[str, list[dict]]:
        self._assert_agent(agent_id)
        return {bucket: list(items) for bucket, items in self._store[agent_id].items()}

    def render_context(self, agent_id: str) -> str:
        context = self.get_context(agent_id)
        return assemble_receiver_context(
            trusted_messages=context["trusted"],
            warning_messages=context["warning"],
            untrusted_messages=context["untrusted"],
            notices=context["safety_notice"],
        )

    def reset(self) -> None:
        self._store = {
            agent_id: {bucket: [] for bucket in CONTEXT_BUCKETS}
            for agent_id in self.agent_ids
        }
