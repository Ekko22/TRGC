from __future__ import annotations

from abc import ABC, abstractmethod


class AttackAdapter(ABC):
    name: str

    @abstractmethod
    def apply(self, message):
        raise NotImplementedError
