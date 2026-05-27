from __future__ import annotations

import networkx as nx


def build_digraph(nodes: list[str], edges: list[tuple[str, str]]) -> nx.DiGraph:
    graph = nx.DiGraph()
    graph.add_nodes_from(nodes)
    graph.add_edges_from(edges)
    return graph
