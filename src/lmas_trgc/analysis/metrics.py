from __future__ import annotations


def recovery_rate(no_defense_score: float, defended_score: float, clean_score: float) -> float:
    denominator = clean_score - no_defense_score
    if denominator == 0:
        return 0.0
    return (defended_score - no_defense_score) / denominator
