from __future__ import annotations

from pydantic import BaseModel, Field

from lmas_trgc.agents.agent_runtime import AgentRuntime
from lmas_trgc.agents.context import AgentContextStore
from lmas_trgc.agents.prompt_builder import PromptBuilder
from lmas_trgc.agents.roles import AgentProfile, get_agent_profile
from lmas_trgc.communication.router import MessageRouter, RouteResult
from lmas_trgc.core.enums import GateAction
from lmas_trgc.defenses.base import DefenseAdapter
from lmas_trgc.llm.client import OpenAICompatibleClient
from lmas_trgc.llm.mock_client import MockLLMClient
from lmas_trgc.runners.protocol import ProtocolManager
from lmas_trgc.tasks.schema import TaskPacket
from lmas_trgc.topology.manager import TopologyManager


def describe_single_run(config: dict) -> dict:
    return {"stage": config.get("stage", "unknown"), "status": "described"}


class SingleRunConfig(BaseModel):
    run_id: str
    topology: str
    attack_type: str
    defense_name: str
    use_mock_llm: bool = True
    max_steps: int | None = None


class MessageEvent(BaseModel):
    step_id: int
    sender: str
    receiver: str
    message_id: str
    delivered: bool
    gate_action: str
    context_bucket: str
    blocked: bool
    downweighted: bool
    rerouted_to_sv: bool
    reason: str | None = None
    route_meta: dict = Field(default_factory=dict)


class SingleRunResult(BaseModel):
    run_id: str
    task_id: str
    topology: str
    attack_type: str
    defense_name: str
    completed: bool
    final_agent: str
    final_context: str
    message_events: list[MessageEvent]
    total_messages: int
    delivered_messages: int
    blocked_messages: int
    downweighted_messages: int
    rerouted_messages: int


class SingleRunExecutor:
    def __init__(
        self,
        topology_manager: TopologyManager,
        protocol_manager: ProtocolManager,
        agent_profiles: dict[str, AgentProfile],
        defense_adapter: DefenseAdapter,
        llm_clients_by_agent: dict[str, MockLLMClient | OpenAICompatibleClient],
        prompt_builder: PromptBuilder,
    ) -> None:
        self.topology_manager = topology_manager
        self.protocol_manager = protocol_manager
        self.agent_profiles = agent_profiles
        self.defense_adapter = defense_adapter
        self.llm_clients_by_agent = llm_clients_by_agent
        self.prompt_builder = prompt_builder

    def _bucket_for_result(self, result: RouteResult) -> str:
        if result.gate_action == GateAction.ALLOW:
            return "trusted"
        if result.gate_action == GateAction.WARN:
            return "warning"
        if result.gate_action == GateAction.DOWNWEIGHT:
            return "untrusted"
        return "safety_notice"

    def _context_content(self, result: RouteResult, content: str) -> str:
        if result.gate_action == GateAction.BLOCK:
            return f"[Safety Notice] A message was blocked before delivery. Reason: {result.reason or 'unspecified'}"
        if result.gate_action == GateAction.REROUTE_TO_SV:
            return f"[Safety Notice] A message required verifier review before delivery. Reason: {result.reason or 'unspecified'}"
        return content

    def run(self, task_packet: TaskPacket, config: SingleRunConfig) -> SingleRunResult:
        router = MessageRouter(self.topology_manager, self.defense_adapter)
        context_store = AgentContextStore(list(self.agent_profiles))
        runtimes = {
            agent_id: AgentRuntime(
                agent_profile=profile,
                llm_client=self.llm_clients_by_agent[agent_id],
                prompt_builder=self.prompt_builder,
            )
            for agent_id, profile in self.agent_profiles.items()
        }

        events: list[MessageEvent] = []
        parent_message_id: str | None = None
        for step_id, protocol_edge in self.protocol_manager.iter_edges(config.topology):
            if config.max_steps is not None and step_id > config.max_steps:
                continue
            sender_profile = get_agent_profile(protocol_edge.sender, self.agent_profiles)
            receiver_profile = get_agent_profile(protocol_edge.receiver, self.agent_profiles)
            rendered_context = context_store.render_context(protocol_edge.sender)
            message = runtimes[protocol_edge.sender].generate_message(
                task_packet=task_packet,
                receiver_profile=receiver_profile,
                message_type=protocol_edge.message_type,
                rendered_context=rendered_context,
                round_id=step_id,
                parent_message_id=parent_message_id,
                protocol_purpose=protocol_edge.purpose,
            )
            result = router.route(
                message,
                topology=config.topology,
                source_model=self.llm_clients_by_agent[protocol_edge.sender].list_models()[0],
                injected_by_attack=False,
                attack_type=config.attack_type,
            )
            bucket = self._bucket_for_result(result)
            context_store.add_message(
                protocol_edge.receiver,
                bucket,
                self._context_content(result, message.content),
                message.message_id,
            )
            events.append(
                MessageEvent(
                    step_id=step_id,
                    sender=protocol_edge.sender,
                    receiver=protocol_edge.receiver,
                    message_id=message.message_id,
                    delivered=result.delivered,
                    gate_action=str(result.gate_action.value),
                    context_bucket=bucket,
                    blocked=result.blocked,
                    downweighted=result.downweighted,
                    rerouted_to_sv=result.rerouted_to_sv,
                    reason=result.reason,
                    route_meta=result.route_meta,
                )
            )
            parent_message_id = message.message_id

        delivered = sum(1 for event in events if event.delivered)
        blocked = sum(1 for event in events if event.blocked)
        downweighted = sum(1 for event in events if event.downweighted)
        rerouted = sum(1 for event in events if event.rerouted_to_sv)
        return SingleRunResult(
            run_id=config.run_id,
            task_id=task_packet.task.task_id,
            topology=config.topology,
            attack_type=config.attack_type,
            defense_name=config.defense_name,
            completed=True,
            final_agent="A7",
            final_context=context_store.render_context("A7"),
            message_events=events,
            total_messages=len(events),
            delivered_messages=delivered,
            blocked_messages=blocked,
            downweighted_messages=downweighted,
            rerouted_messages=rerouted,
        )
