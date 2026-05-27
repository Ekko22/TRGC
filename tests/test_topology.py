from lmas_trgc.topology.manager import TopologyManager


def test_topologies_load_and_exclude_sv():
    manager = TopologyManager()
    assert manager.list_topologies() == ["chain", "graph", "star", "tree"]
    for topology in manager.list_topologies():
        assert "SV" not in manager.get_nodes(topology)
        assert manager.get_critical_nodes(topology) == ["A1", "A6", "A7"]


def test_required_edges():
    manager = TopologyManager()
    assert manager.is_allowed_edge("chain", "A1", "A2") is True
    assert manager.is_allowed_edge("chain", "A2", "A1") is False
    assert manager.is_allowed_edge("graph", "A3", "A7") is True
    assert manager.is_allowed_edge("tree", "A1", "A2") is True
