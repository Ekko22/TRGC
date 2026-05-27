from enum import StrEnum


class AgentRole(StrEnum):
    PLANNER = "planner"
    CONSTRAINT_FACT_EXTRACTOR = "constraint_fact_extractor"
    WORKER_A = "worker_a"
    WORKER_B = "worker_b"
    CRITIC_TESTER = "critic_tester"
    DOMAIN_REVIEWER = "domain_reviewer"
    FINALIZER_EXECUTOR = "finalizer_executor"
    TRUSTED_SAFETY_VERIFIER = "trusted_safety_verifier"


class TopologyType(StrEnum):
    STAR = "star"
    CHAIN = "chain"
    GRAPH = "graph"
    TREE = "tree"


class AttackType(StrEnum):
    NONE = "none"
    MESSAGE_POISONING = "message_poisoning"
    ROLE_IMPERSONATION = "role_impersonation"
    RELAY_INJECTION = "relay_injection"


class DefenseType(StrEnum):
    NO_DEFENSE = "no_defense"
    SIMPLE_CONTENT_GUARDRAIL = "simple_content_guardrail"
    FULL_CHECKING_LIGHT = "full_checking_light"
    GSAFEGUARD = "gsafeguard"
    TRGC = "trgc"


class GateAction(StrEnum):
    ALLOW = "allow"
    WARN = "warn"
    DOWNWEIGHT = "downweight"
    REROUTE_TO_SV = "reroute_to_sv"
    BLOCK = "block"
    LIMIT_FANOUT = "limit_fanout"


class MessageType(StrEnum):
    TASK_ASSIGNMENT = "task_assignment"
    FACT_EXTRACTION = "fact_extraction"
    INTERMEDIATE_RESULT = "intermediate_result"
    CRITIQUE = "critique"
    REVIEW = "review"
    FINALIZATION = "finalization"
    SAFETY_NOTICE = "safety_notice"
    SV_VERDICT = "sv_verdict"
