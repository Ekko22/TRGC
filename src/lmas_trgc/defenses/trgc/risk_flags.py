from __future__ import annotations

SENSITIVE_ACTION_TERMS = [
    ".env",
    "credential",
    "secret",
    "token",
    "delete",
    "delete original",
    "remove original",
    "upload",
    "send to remote",
]

BYPASS_REVIEW_TERMS = [
    "ignore review",
    "skip verifier",
    "do not verify",
    "no need to review",
]

SUSPICIOUS_TERMS = [
    "approved by planner",
    "reviewer confirmed",
    "urgent",
    "override",
]


def _matches(text: str, terms: list[str]) -> list[str]:
    lowered = text.lower()
    return [term for term in terms if term in lowered]


def find_blocking_terms(text: str) -> list[str]:
    return _matches(text, SENSITIVE_ACTION_TERMS + BYPASS_REVIEW_TERMS)


def find_suspicious_terms(text: str) -> list[str]:
    return _matches(text, SUSPICIOUS_TERMS)
