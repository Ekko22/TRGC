from __future__ import annotations

from itertools import product


def enumerate_matrix(topologies: list[str], attacks: list[str], defenses: list[str]) -> list[tuple[str, str, str]]:
    return list(product(topologies, attacks, defenses))
