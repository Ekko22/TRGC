from lmas_trgc.communication.message import AgentMessage
from lmas_trgc.communication.router import MessageRouter
from lmas_trgc.defenses.trgc.controller import TRGCAdapter
from lmas_trgc.llm.mock_client import MockLLMClient
from lmas_trgc.topology.manager import TopologyManager


def test_mock_run_routes_without_real_llm_or_network():
    client = MockLLMClient()
    response = client.chat([{"role": "user", "content": "Draft a small result."}], model="mock")
    message = AgentMessage(
        message_id="msg_mock",
        parent_message_id=None,
        round_id=0,
        sender="A1",
        receiver="A2",
        sender_role="Planner",
        receiver_role="ConstraintFactExtractor",
        message_type="task_assignment",
        content=response["content"],
        reasoning_summary=None,
        confidence=0.9,
        task_id="task_mock",
    )
    router = MessageRouter(TopologyManager(), TRGCAdapter())
    result = router.route(message, "chain", source_model=response["model"])
    assert result.delivered is True
    assert result.route_meta["exposure_level"] in {"low", "medium", "high"}
