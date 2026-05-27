from __future__ import annotations


def estimate_tokens_from_text(text: str | None) -> int:
    value = text or ""
    return max(1, len(value) // 4)


def estimate_tokens_from_messages(messages: list[dict]) -> int:
    total_chars = 0
    for message in messages:
        total_chars += len(str(message.get("content") or ""))
    return max(1, total_chars // 4)


def estimate_tokens(text: str | None) -> int:
    return estimate_tokens_from_text(text)
