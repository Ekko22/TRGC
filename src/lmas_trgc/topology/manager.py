from __future__ import annotations

from pathlib import Path

import networkx as nx

from lmas_trgc.core.config import ConfigError, load_yaml


class TopologyManager:
    def __init__(self, config_path: str | Path = "configs/topologies.yaml") -> None:
        raw = load_yaml(config_path)
        self._topologies: dict[str, dict] = raw.get("topologies", {})
        if not self._topologies:
            raise ConfigError("No topologies configured.")
        self._graphs: dict[str, nx.DiGraph] = {}
        for name, spec in self._topologies.items():
            nodes = list(spec.get("nodes", []))
            edges = [tuple(edge) for edge in spec.get("edges", [])]
            graph = nx.DiGraph()
            graph.add_nodes_from(nodes)
            graph.add_edges_from(edges)
            self._graphs[name] = graph
        self.assert_sv_not_in_task_topology()

    def list_topologies(self) -> list[str]:
        return sorted(self._topologies)

    def _spec(self, topology: str) -> dict:
        if topology not in self._topologies:
            raise KeyError(f"Unknown topology: {topology}")
        return self._topologies[topology]

    def _graph(self, topology: str) -> nx.DiGraph:
        self._spec(topology)
        return self._graphs[topology]

    def _assert_node(self, topology: str, node: str) -> None:
        if node not in self._graph(topology):
            raise KeyError(f"Node {node!r} is not in topology {topology!r}")

    def get_nodes(self, topology: str) -> list[str]:
        return list(self._spec(topology).get("nodes", []))

    def get_edges(self, topology: str) -> list[tuple[str, str]]:
        return [tuple(edge) for edge in self._spec(topology).get("edges", [])]

    def get_critical_nodes(self, topology: str) -> list[str]:
        return list(self._spec(topology).get("critical_nodes", []))

    def is_allowed_edge(self, topology: str, sender: str, receiver: str) -> bool:
        self._assert_node(topology, sender)
        self._assert_node(topology, receiver)
        return self._graph(topology).has_edge(sender, receiver)

    def outgoing_neighbors(self, topology: str, node: str) -> list[str]:
        self._assert_node(topology, node)
        return list(self._graph(topology).successors(node))

    def downstream_reachable_nodes(self, topology: str, node: str) -> list[str]:
        self._assert_node(topology, node)
        return sorted(nx.descendants(self._graph(topology), node))

    def critical_nodes_reachable(self, topology: str, node: str) -> list[str]:
        reachable = set(self.downstream_reachable_nodes(topology, node))
        critical = set(self.get_critical_nodes(topology))
        return sorted(reachable & critical)

    def fanout_count(self, topology: str, node: str) -> int:
        return len(self.outgoing_neighbors(topology, node))

    def assert_sv_not_in_task_topology(self) -> None:
        for name, spec in self._topologies.items():
            nodes = set(spec.get("nodes", []))
            critical = set(spec.get("critical_nodes", []))
            edges = [tuple(edge) for edge in spec.get("edges", [])]
            if "SV" in nodes or "SV" in critical or any("SV" in edge for edge in edges):
                raise ConfigError(f"SV must not appear in task topology {name!r}")
