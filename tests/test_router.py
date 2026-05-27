from lmas_trgc.communication.message import AgentMessage
from lmas_trgc.communication.router import MessageRouter
from lmas_trgc.defenses.no_defense import NoDefenseAdapter
from lmas_trgc.topology.manager import TopologyManager


def _message(sender="A1", receiver="A2"):
    return AgentMessage(
        message_id="msg_route",
        parent_message_id=None,
        round_id=0,
        sender=sender,
        receiver=receiver,
        sender_role="Planner",
        receiver_role="Worker",
        message_type="task_assignment",
        content="Please solve this subtask.",
        reasoning_summary=None,
        confidence=0.9,
        task_id="task_route",
    )


def test_legal_edge_no_defense_delivers():
    router = MessageRouter(TopologyManager(), NoDefenseAdapter())
    result = router.route(_message(), "chain")
    assert result.delivered is True
    assert result.blocked is False


def test_illegal_edge_blocks():
    router = MessageRouter(TopologyManager(), NoDefenseAdapter())
    result = router.route(_message(sender="A2", receiver="A1"), "chain")
    assert result.delivered is False
    assert result.blocked is True


def test_route_meta_contains_exposure_fields():
    router = MessageRouter(TopologyManager(), NoDefenseAdapter())
    result = router.route(_message(), "chain")
    assert "exposure_level" in result.route_meta
    assert "fanout_count" in result.route_meta
    assert "critical_nodes_reachable" in result.route_meta
