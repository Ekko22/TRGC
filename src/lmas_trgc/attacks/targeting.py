from __future__ import annotations

from lmas_trgc.tasks.schema import TaskPacket

CRITICAL_RECEIVERS = {"A1", "A6", "A7"}
CHAIN_MIDDLE_EDGES = {("A3", "A4"), ("A4", "A5"), ("A5", "A6")}
GRAPH_DIRECT_TO_FINALIZER = {("A3", "A7"), ("A4", "A7")}
TREE_BRANCH_SUMMARY_EDGES = {("A2", "A1"), ("A6", "A1")}


def is_high_value_receiver(receiver: str) -> bool:
    return receiver in CRITICAL_RECEIVERS


def is_middle_chain_edge(sender: str, receiver: str, topology: str) -> bool:
    return topology == "chain" and (sender, receiver) in CHAIN_MIDDLE_EDGES


def is_direct_to_finalizer(sender: str, receiver: str) -> bool:
    return receiver == "A7"


def should_attack_edge(route_meta: dict, attack_type: str) -> bool:
    if attack_type == "none":
        return False
    sender = route_meta.get("sender")
    receiver = route_meta.get("receiver")
    topology = route_meta.get("topology")
    if not sender or not receiver or not topology:
        return False
    edge = (sender, receiver)
    if attack_type == "message_poisoning":
        return receiver in CRITICAL_RECEIVERS and sender in {"A2", "A3", "A4", "A5", "A6"}
    if attack_type == "role_impersonation":
        return is_high_value_receiver(receiver)
    if attack_type == "relay_injection":
        return (
            edge in GRAPH_DIRECT_TO_FINALIZER
            or edge in TREE_BRANCH_SUMMARY_EDGES
            or is_middle_chain_edge(sender, receiver, topology)
            or bool(route_meta.get("is_forwarded_path"))
        )
    return False


def choose_target_slot(task_packet: TaskPacket, attack_type: str) -> str | None:
    slots = list(task_packet.attack_surface.get("target_slots", []))
    anchor_types = [anchor.anchor_type for anchor in task_packet.anchors]
    preferences = [
        "forbidden_action",
        "permission",
        "safety_requirement",
        "numeric",
        "code_spec",
        "logic_rule",
    ]
    for preferred in preferences:
        if preferred in slots or preferred in anchor_types:
            return preferred
    return slots[0] if slots else None
