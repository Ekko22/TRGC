from __future__ import annotations

import re


def normalize_text(text: object, *, lowercase: bool = False) -> str:
    if text is None:
        return ""
    normalized = re.sub(r"\s+", " ", str(text).strip())
    return normalized.lower() if lowercase else normalized


def normalize_for_exact_match(text: object) -> str:
    normalized = normalize_text(text, lowercase=True)
    return normalized.rstrip(".,;:!?")


def normalize_answer(answer: str) -> str:
    return normalize_for_exact_match(answer)


def extract_final_answer(text: str) -> str:
    source = str(text or "")
    for marker in ("Final answer:", "Answer:"):
        match = re.search(re.escape(marker) + r"\s*(.+)", source, flags=re.IGNORECASE)
        if match:
            return normalize_text(match.group(1).splitlines()[0])
    match = re.search(r"Therefore,\s*(.+)", source, flags=re.IGNORECASE)
    if match:
        return normalize_text(re.split(r"[.!?]\s+", match.group(1), maxsplit=1)[0])
    for line in reversed(source.splitlines()):
        if line.strip():
            return normalize_text(line)
    return normalize_text(source)


def normalize_number(text: object) -> str | None:
    matches = re.findall(r"[-+]?\d[\d,]*(?:\.\d+)?", normalize_text(text))
    if not matches:
        return None
    value = matches[-1].replace(",", "")
    try:
        number = float(value)
    except ValueError:
        return value
    if number.is_integer():
        return str(int(number))
    return str(number).rstrip("0").rstrip(".")


def normalize_choice(text: object) -> str | None:
    normalized = normalize_text(text)
    exact = re.fullmatch(r"\(?\s*([A-Ea-e])\s*\)?\.?", normalized)
    if exact:
        return exact.group(1).upper()
    match = re.search(r"(?:answer\s+is|answer|option|choice)\s*[:\s]*\(?([A-Ea-e])\)?", normalized, re.IGNORECASE)
    if match:
        return match.group(1).upper()
    return None


def contains_any(text: str, patterns: list[str]) -> bool:
    lower = str(text or "").lower()
    return any(pattern.lower() in lower for pattern in patterns)
