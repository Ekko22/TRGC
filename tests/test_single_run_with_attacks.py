from lmas_trgc.agents.prompt_builder import PromptBuilder
from lmas_trgc.agents.roles import load_agent_profiles
from lmas_trgc.attacks.manager import AttackManager
from lmas_trgc.defenses.factory import create_defense_adapter
from lmas_trgc.defenses.trgc.safety_verifier import SafetyVerifier
from lmas_trgc.llm.mock_client import MockLLMClient
from lmas_trgc.runners.protocol import ProtocolManager
from lmas_trgc.runners.single_run import SingleRunConfig, SingleRunExecutor
from lmas_trgc.tasks.anchors import build_task_packet
from lmas_trgc.tasks.local_synthetic import generate_local_mas_safety_set
from lmas_trgc.topology.manager import TopologyManager


def _run(topology: str, attack: str, defense: str):
    topology_manager = TopologyManager()
    profiles = load_agent_profiles()
    verifier = SafetyVerifier(mode="mock")
    executor = SingleRunExecutor(
        topology_manager=topology_manager,
        protocol_manager=ProtocolManager(topology_manager=topology_manager),
        agent_profiles=profiles,
        defense_adapter=create_defense_adapter(defense, topology_manager, safety_verifier=verifier),
        llm_clients_by_agent={agent_id: MockLLMClient(model_name=f"mock-{agent_id}") for agent_id in profiles},
        prompt_builder=PromptBuilder(),
        attack_manager=AttackManager(attack),
    )
    return executor.run(
        build_task_packet(generate_local_mas_safety_set(1)[0]),
        SingleRunConfig(
            run_id=f"attack_{topology}_{attack}_{defense}",
            topology=topology,
            attack_type=attack,
            defense_name=defense,
            use_mock_llm=True,
        ),
    )


def test_graph_message_poisoning_no_defense_injects():
    result = _run("graph", "message_poisoning", "no_defense")
    assert result.completed is True
    assert result.attacked_messages > 0
    assert any(event.attack_injected for event in result.message_events)


def test_graph_role_impersonation_trgc_completes():
    result = _run("graph", "role_impersonation", "trgc")
    assert result.completed is True
    assert result.attacked_messages > 0


def test_graph_relay_injection_trgc_completes():
    result = _run("graph", "relay_injection", "trgc")
    assert result.completed is True
    assert result.attacked_messages > 0


def test_chain_message_poisoning_trgc_completes():
    result = _run("chain", "message_poisoning", "trgc")
    assert result.completed is True
    assert result.attacked_messages > 0


def test_tree_relay_injection_trgc_completes_and_block_notice_hides_payload():
    result = _run("tree", "relay_injection", "trgc")
    assert result.completed is True
    assert result.attacked_messages > 0
    if result.blocked_messages:
        assert "Injected communication update" not in result.final_context


def test_message_event_attack_fields_exist():
    result = _run("graph", "message_poisoning", "trgc")
    event = result.message_events[0]
    assert hasattr(event, "attack_injected")
    assert hasattr(event, "attack_changed_fields")
