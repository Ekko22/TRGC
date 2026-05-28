from __future__ import annotations

from datetime import datetime, timezone

from lmas_trgc.core.ids import stable_hash
from lmas_trgc.logging.schemas import MessageEventRecord, RunSummaryRecord, TopologyEventRecord
from lmas_trgc.runners.single_run import SingleRunResult
from lmas_trgc.tasks.schema import TaskPacket


def _created_at() -> str:
    return datetime.now(timezone.utc).isoformat()


def build_run_summary_record(
    result: SingleRunResult,
    task_packet: TaskPacket,
    created_at: str | None = None,
) -> RunSummaryRecord:
    return RunSummaryRecord(
        run_id=result.run_id,
        task_id=result.task_id,
        dataset=task_packet.task.dataset,
        domain=task_packet.task.domain,
        topology=result.topology,
        attack_type=result.attack_type,
        defense_name=result.defense_name,
        completed=result.completed,
        final_agent=result.final_agent,
        total_messages=result.total_messages,
        total_llm_calls=result.total_llm_calls,
        total_input_tokens=result.total_input_tokens,
        total_output_tokens=result.total_output_tokens,
        total_tokens=result.total_tokens,
        delivered_messages=result.delivered_messages,
        blocked_messages=result.blocked_messages,
        downweighted_messages=result.downweighted_messages,
        rerouted_messages=result.rerouted_messages,
        attacked_messages=result.attacked_messages,
        final_context_hash=stable_hash(result.final_context, length=24),
        final_output_hash=stable_hash(result.final_output or result.final_context, length=24),
        created_at=created_at or _created_at(),
        metadata={
            "final_context_chars": len(result.final_context),
            "final_output_chars": len(result.final_output or result.final_context),
            "message_event_count": len(result.message_events),
        },
    )


def build_message_event_records(
    result: SingleRunResult,
    task_id: str,
    topology: str,
) -> list[MessageEventRecord]:
    records: list[MessageEventRecord] = []
    for event in result.message_events:
        route_meta = event.route_meta
        records.append(
            MessageEventRecord(
                run_id=result.run_id,
                task_id=task_id,
                step_id=event.step_id,
                sender=event.sender,
                receiver=event.receiver,
                message_id=event.message_id,
                delivered=event.delivered,
                gate_action=event.gate_action,
                context_bucket=event.context_bucket,
                blocked=event.blocked,
                downweighted=event.downweighted,
                rerouted_to_sv=event.rerouted_to_sv,
                reason=event.reason,
                attack_injected=event.attack_injected,
                attack_type=event.attack_type,
                attack_changed_fields=event.attack_changed_fields,
                topology=topology,
                topology_edge=route_meta.get("edge") or route_meta.get("topology_edge"),
                fanout_count=route_meta.get("fanout_count"),
                critical_nodes_reachable=list(route_meta.get("critical_nodes_reachable", [])),
                exposure_level=route_meta.get("exposure_level"),
                content_hash=None,
                source_model=event.source_model,
                input_tokens=event.input_tokens,
                output_tokens=event.output_tokens,
                total_tokens=event.total_tokens,
                metadata={"route_meta_keys": sorted(route_meta)},
            )
        )
    return records


def build_topology_event_records(
    result: SingleRunResult,
    task_id: str,
    topology: str,
) -> list[TopologyEventRecord]:
    critical_nodes = {"A1", "A6", "A7"}
    records: list[TopologyEventRecord] = []
    for event in result.message_events:
        records.append(
            TopologyEventRecord(
                run_id=result.run_id,
                task_id=task_id,
                topology=topology,
                step_id=event.step_id,
                edge=f"{event.sender}->{event.receiver}",
                sender=event.sender,
                receiver=event.receiver,
                gate_action=event.gate_action,
                delivered=event.delivered,
                blocked=event.blocked,
                downweighted=event.downweighted,
                rerouted_to_sv=event.rerouted_to_sv,
                attack_injected=event.attack_injected,
                is_critical_receiver=event.receiver in critical_nodes,
                critical_nodes_reachable=list(event.route_meta.get("critical_nodes_reachable", [])),
            )
        )
    return records
