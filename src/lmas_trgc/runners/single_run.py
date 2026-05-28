from __future__ import annotations

from pydantic import BaseModel, Field

from lmas_trgc.agents.agent_runtime import AgentRuntime
from lmas_trgc.agents.context import AgentContextStore
from lmas_trgc.agents.prompt_builder import PromptBuilder
from lmas_trgc.agents.roles import AgentProfile, get_agent_profile
from lmas_trgc.attacks.manager import AttackManager
from lmas_trgc.communication.router import MessageRouter, RouteResult
from lmas_trgc.core.enums import GateAction
from lmas_trgc.defenses.base import DefenseAdapter
from lmas_trgc.llm.client import OpenAICompatibleClient
from lmas_trgc.llm.mock_client import MockLLMClient
from lmas_trgc.llm.usage import LLMUsageRecord, merge_usage_records
from lmas_trgc.runners.protocol import ProtocolManager
from lmas_trgc.tasks.schema import TaskPacket
from lmas_trgc.topology.exposure import estimate_topology_exposure
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
    attack_injected: bool = False
    attack_type: str | None = None
    attack_changed_fields: list[str] = Field(default_factory=list)
    reason: str | None = None
    route_meta: dict = Field(default_factory=dict)
    source_model: str | None = None
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0


class SingleRunResult(BaseModel):
    run_id: str
    task_id: str
    topology: str
    attack_type: str
    defense_name: str
    completed: bool
    final_agent: str
    final_context: str
    final_output: str = ""
    message_events: list[MessageEvent]
    total_messages: int
    delivered_messages: int
    blocked_messages: int
    downweighted_messages: int
    rerouted_messages: int
    attacked_messages: int
    total_llm_calls: int = 0
    total_input_tokens: int = 0
    total_output_tokens: int = 0
    total_tokens: int = 0
    model_usage: dict = Field(default_factory=dict)


class SingleRunExecutor:
    def __init__(
        self,
        topology_manager: TopologyManager,
        protocol_manager: ProtocolManager,
        agent_profiles: dict[str, AgentProfile],
        defense_adapter: DefenseAdapter,
        llm_clients_by_agent: dict[str, MockLLMClient | OpenAICompatibleClient],
        prompt_builder: PromptBuilder,
        attack_manager: AttackManager | None = None,
    ) -> None:
        self.topology_manager = topology_manager
        self.protocol_manager = protocol_manager
        self.agent_profiles = agent_profiles
        self.defense_adapter = defense_adapter
        self.llm_clients_by_agent = llm_clients_by_agent
        self.prompt_builder = prompt_builder
        self.attack_manager = attack_manager

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
            sender = result.route_meta.get("sender", "unknown")
            receiver = result.route_meta.get("receiver", "unknown")
            return (
                f"[Safety Notice] A message from {sender} to {receiver} was blocked before delivery. "
                f"Reason: {result.reason or 'unspecified'}"
            )
        if result.gate_action == GateAction.REROUTE_TO_SV:
            return f"[Safety Notice] A message required verifier review before delivery. Reason: {result.reason or 'unspecified'}"
        return content

    def _source_model_for_client(self, client: MockLLMClient | OpenAICompatibleClient) -> str | None:
        return getattr(client, "model_name", None)

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
        usage_records: list[LLMUsageRecord] = []
        parent_message_id: str | None = None
        last_a7_delivery_content: str | None = None
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
            exposure = estimate_topology_exposure(self.topology_manager, config.topology, message.receiver)
            preliminary_route_meta = {
                "topology": config.topology,
                "edge": f"{message.sender}->{message.receiver}",
                "sender": message.sender,
                "receiver": message.receiver,
                "step_id": step_id,
                "message_type": protocol_edge.message_type,
                "edge_allowed": self.topology_manager.is_allowed_edge(config.topology, message.sender, message.receiver),
                "fanout_count": exposure["fanout_count"],
                "critical_nodes_reachable": exposure["critical_nodes_reachable"],
                "exposure_level": exposure["exposure_level"],
                "is_forwarded_path": message.is_forwarded,
            }
            attack_result = None
            routed_message = message
            if self.attack_manager is not None:
                routed_message, attack_result = self.attack_manager.apply_attack_if_needed(
                    message,
                    preliminary_route_meta,
                    task_packet,
                )
            attack_injected = bool(attack_result and attack_result.attacked)
            effective_attack_type = attack_result.attack_type if attack_injected else None
            attack_changed_fields = attack_result.changed_fields if attack_injected else []
            usage_meta = routed_message.metadata.get("llm_usage", {})
            source_model = usage_meta.get("model") or self._source_model_for_client(self.llm_clients_by_agent[protocol_edge.sender])
            input_tokens = int(usage_meta.get("input_tokens") or 0)
            output_tokens = int(usage_meta.get("output_tokens") or 0)
            total_tokens = int(usage_meta.get("total_tokens") or input_tokens + output_tokens)
            call_count = int(usage_meta.get("call_count") or 0)
            usage_records.append(
                LLMUsageRecord(
                    agent_id=protocol_edge.sender,
                    model_name=source_model,
                    input_tokens=input_tokens,
                    output_tokens=output_tokens,
                    total_tokens=total_tokens,
                    call_count=call_count,
                )
            )
            result = router.route(
                routed_message,
                topology=config.topology,
                source_model=source_model,
                injected_by_attack=attack_injected,
                attack_type=effective_attack_type,
            )
            event_route_meta = {**preliminary_route_meta, **result.route_meta}
            bucket = self._bucket_for_result(result)
            context_store.add_message(
                protocol_edge.receiver,
                bucket,
                self._context_content(result, routed_message.content),
                routed_message.message_id,
            )
            if result.delivered and protocol_edge.receiver == "A7":
                last_a7_delivery_content = routed_message.content
            events.append(
                MessageEvent(
                    step_id=step_id,
                    sender=protocol_edge.sender,
                    receiver=protocol_edge.receiver,
                    message_id=routed_message.message_id,
                    delivered=result.delivered,
                    gate_action=str(result.gate_action.value),
                    context_bucket=bucket,
                    blocked=result.blocked,
                    downweighted=result.downweighted,
                    rerouted_to_sv=result.rerouted_to_sv,
                    attack_injected=attack_injected,
                    attack_type=effective_attack_type,
                    attack_changed_fields=attack_changed_fields,
                    reason=result.reason,
                    route_meta=event_route_meta,
                    source_model=source_model,
                    input_tokens=input_tokens,
                    output_tokens=output_tokens,
                    total_tokens=total_tokens,
                )
            )
            parent_message_id = routed_message.message_id

        delivered = sum(1 for event in events if event.delivered)
        blocked = sum(1 for event in events if event.blocked)
        downweighted = sum(1 for event in events if event.downweighted)
        rerouted = sum(1 for event in events if event.rerouted_to_sv)
        attacked = sum(1 for event in events if event.attack_injected)
        final_context = context_store.render_context("A7")
        usage_summary = merge_usage_records(usage_records)
        return SingleRunResult(
            run_id=config.run_id,
            task_id=task_packet.task.task_id,
            topology=config.topology,
            attack_type=config.attack_type,
            defense_name=config.defense_name,
            completed=True,
            final_agent="A7",
            final_context=final_context,
            final_output=last_a7_delivery_content or final_context,
            message_events=events,
            total_messages=len(events),
            delivered_messages=delivered,
            blocked_messages=blocked,
            downweighted_messages=downweighted,
            rerouted_messages=rerouted,
            attacked_messages=attacked,
            total_llm_calls=usage_summary.total_llm_calls,
            total_input_tokens=usage_summary.total_input_tokens,
            total_output_tokens=usage_summary.total_output_tokens,
            total_tokens=usage_summary.total_tokens,
            model_usage=usage_summary.model_dump(mode="json"),
        )
