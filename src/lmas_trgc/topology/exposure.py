from __future__ import annotations

from lmas_trgc.topology.manager import TopologyManager


def estimate_topology_exposure(
    topology_manager: TopologyManager, topology: str, receiver: str
) -> dict:
    reachable_nodes = topology_manager.downstream_reachable_nodes(topology, receiver)
    critical_reachable = topology_manager.critical_nodes_reachable(topology, receiver)
    fanout = topology_manager.fanout_count(topology, receiver)
    critical_nodes = set(topology_manager.get_critical_nodes(topology))

    if len(critical_reachable) >= 2 or fanout >= 3:
        exposure_level = "high"
    elif receiver in critical_nodes or critical_reachable:
        exposure_level = "medium"
    else:
        exposure_level = "low"

    return {
        "receiver": receiver,
        "reachable_nodes": reachable_nodes,
        "critical_nodes_reachable": critical_reachable,
        "fanout_count": fanout,
        "exposure_level": exposure_level,
    }
