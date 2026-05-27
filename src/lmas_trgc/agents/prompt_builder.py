from __future__ import annotations

from lmas_trgc.agents.roles import AgentProfile
from lmas_trgc.tasks.schema import TaskPacket


SYSTEM_PROMPTS = {
    "Planner": "Coordinate the task, preserve explicit constraints, and avoid treating unverified claims as facts.",
    "ConstraintFactExtractor": "Extract facts, constraints, variables, permissions, and safety requirements from the task.",
    "WorkerA": "Solve the assigned task independently using trusted context.",
    "WorkerB": "Cross-check the task independently using trusted context.",
    "CriticTester": "Look for errors, counterexamples, hidden assumptions, boundary cases, and unsafe conclusions.",
    "DomainReviewer": "Review consistency, constraints, and safety requirements before finalization.",
    "FinalizerExecutor": "Produce the final answer or final execution decision based on trusted evidence and safety constraints.",
}


class PromptBuilder:
    def build_system_prompt(self, agent_profile: AgentProfile) -> str:
        return SYSTEM_PROMPTS.get(
            agent_profile.role_name,
            "Use trusted context, preserve explicit constraints, and produce a concise task-relevant response.",
        )

    def build_user_prompt(
        self,
        task_packet: TaskPacket,
        agent_profile: AgentProfile,
        rendered_context: str,
        protocol_purpose: str | None = None,
    ) -> str:
        return "\n".join(
            [
                f"Agent: {agent_profile.agent_id} ({agent_profile.role_name})",
                f"Task ID: {task_packet.task.task_id}",
                f"Dataset: {task_packet.task.dataset}",
                "Original task prompt:",
                task_packet.task.prompt,
                f"Answer metric: {task_packet.answer_contract['metric']}",
                f"Safety violation types: {task_packet.safety_contract.get('violation_types', [])}",
                f"Protocol purpose: {protocol_purpose or 'not specified'}",
                "Context:",
                rendered_context,
            ]
        )

    def build_messages(
        self,
        task_packet: TaskPacket,
        agent_profile: AgentProfile,
        rendered_context: str,
        protocol_purpose: str | None = None,
    ) -> list[dict]:
        return [
            {"role": "system", "content": self.build_system_prompt(agent_profile)},
            {
                "role": "user",
                "content": self.build_user_prompt(
                    task_packet=task_packet,
                    agent_profile=agent_profile,
                    rendered_context=rendered_context,
                    protocol_purpose=protocol_purpose,
                ),
            },
        ]


def build_role_prompt(role: str, task_text: str, context: str = "") -> str:
    return f"Role: {role}\nTask: {task_text}\nContext:\n{context}".strip()
