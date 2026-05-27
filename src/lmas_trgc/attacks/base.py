from __future__ import annotations

from abc import ABC, abstractmethod

from pydantic import BaseModel, Field

from lmas_trgc.communication.message import AgentMessage
from lmas_trgc.core.ids import stable_hash
from lmas_trgc.tasks.schema import TaskPacket


class AttackDecision(BaseModel):
    should_attack: bool
    attack_type: str
    reason: str | None = None
    target_slot: str | None = None
    metadata: dict = Field(default_factory=dict)


class AttackResult(BaseModel):
    attacked: bool
    attack_type: str
    original_message_id: str
    attacked_message_id: str
    original_content_hash: str
    attacked_content_hash: str
    changed_fields: list[str]
    reason: str | None = None
    metadata: dict = Field(default_factory=dict)


class BaseAttackStrategy(ABC):
    attack_type: str

    @abstractmethod
    def should_attack(
        self,
        message: AgentMessage,
        route_meta: dict,
        task_packet: TaskPacket,
    ) -> AttackDecision:
        raise NotImplementedError

    @abstractmethod
    def apply(
        self,
        message: AgentMessage,
        route_meta: dict,
        task_packet: TaskPacket,
        decision: AttackDecision,
    ) -> tuple[AgentMessage, AttackResult]:
        raise NotImplementedError

    def _result(
        self,
        original: AgentMessage,
        attacked: AgentMessage,
        changed_fields: list[str],
        reason: str | None,
        metadata: dict | None = None,
    ) -> AttackResult:
        return AttackResult(
            attacked=bool(changed_fields),
            attack_type=self.attack_type,
            original_message_id=original.message_id,
            attacked_message_id=attacked.message_id,
            original_content_hash=stable_hash(original.content, length=16),
            attacked_content_hash=stable_hash(attacked.content, length=16),
            changed_fields=changed_fields,
            reason=reason,
            metadata=metadata or {},
        )


class AttackAdapter(ABC):
    name: str

    @abstractmethod
    def apply(self, message):
        raise NotImplementedError
