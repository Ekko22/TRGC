from pathlib import Path

import pytest

from lmas_trgc.runners.protocol import ProtocolManager
from lmas_trgc.topology.manager import TopologyManager


def test_protocols_load_and_edges_are_legal():
    topology_manager = TopologyManager()
    manager = ProtocolManager(topology_manager=topology_manager)
    assert manager.list_protocols() == ["chain", "graph", "star", "tree"]
    for topology in manager.list_protocols():
        previous = 0
        for step_id, edge in manager.iter_edges(topology):
            assert step_id >= previous
            previous = step_id
            assert "SV" not in {edge.sender, edge.receiver}
            assert topology_manager.is_allowed_edge(topology, edge.sender, edge.receiver)


def test_tree_return_edges_are_legal():
    manager = TopologyManager()
    for sender, receiver in [("A3", "A2"), ("A4", "A2"), ("A2", "A1"), ("A6", "A1"), ("A1", "A7")]:
        assert manager.is_allowed_edge("tree", sender, receiver)
    for topology in manager.list_topologies():
        assert "SV" not in manager.get_nodes(topology)


def test_graph_protocol_has_direct_finalizer_risk_edges():
    edges = [(edge.sender, edge.receiver) for _, edge in ProtocolManager().iter_edges("graph")]
    assert ("A3", "A7") in edges
    assert ("A4", "A7") in edges


def test_invalid_protocol_error_mentions_sender_receiver(tmp_path):
    protocol_path = tmp_path / "protocols.yaml"
    protocol_path.write_text(
        """
protocols:
  chain:
    topology: chain
    steps:
      - step_id: 1
        edges:
          - sender: A2
            receiver: A1
            message_type: TASK_ASSIGNMENT
            purpose: invalid edge
""",
        encoding="utf-8",
    )
    with pytest.raises(ValueError) as exc:
        ProtocolManager(protocols_path=protocol_path, topology_manager=TopologyManager())
    text = str(exc.value)
    assert "sender=A2" in text
    assert "receiver=A1" in text
