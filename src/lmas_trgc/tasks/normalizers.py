from __future__ import annotations

import json
import re
from decimal import Decimal, InvalidOperation
from typing import Any


def normalize_text(value: object, *, preserve_newlines: bool = False) -> str:
    if value is None:
        return ""
    if isinstance(value, (list, tuple)):
        text = "\n".join(normalize_text(item, preserve_newlines=preserve_newlines) for item in value)
    elif isinstance(value, dict):
        text = json.dumps(value, ensure_ascii=False, sort_keys=True)
    else:
        text = str(value).strip()
    if preserve_newlines:
        lines = [re.sub(r"[ \t]+", " ", line).strip() for line in text.splitlines()]
        return "\n".join(line for line in lines if line)
    return re.sub(r"\s+", " ", text).strip()


def normalize_answer(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, (int, float, Decimal)):
        try:
            return format(Decimal(str(value)).normalize(), "f").rstrip("0").rstrip(".") or "0"
        except InvalidOperation:
            return str(value).strip()
    text = str(value).strip()
    if re.fullmatch(r"[a-zA-Z]", text):
        return text.upper()
    try:
        if re.fullmatch(r"[-+]?\d+", text):
            sign = "-" if text.startswith("-") else ""
            digits = text.lstrip("+-").lstrip("0") or "0"
            return sign + digits
        if re.fullmatch(r"[-+]?\d+\.\d+", text):
            normalized = format(Decimal(text).normalize(), "f")
            return normalized.rstrip("0").rstrip(".") or "0"
    except InvalidOperation:
        pass
    return text


def normalize_choices(value: object) -> list[str]:
    if value is None:
        return []
    if isinstance(value, dict):
        labels = value.get("label")
        texts = value.get("text")
        if isinstance(labels, list) and isinstance(texts, list):
            return [
                f"{normalize_text(label)}. {normalize_text(text)}"
                for label, text in zip(labels, texts)
                if normalize_text(text)
            ]
        return [
            f"{normalize_text(key)}. {normalize_text(item)}"
            for key, item in value.items()
            if normalize_text(item)
        ]
    if isinstance(value, list):
        choices: list[str] = []
        for index, item in enumerate(value):
            default_label = chr(ord("A") + index)
            if isinstance(item, dict):
                label = item.get("label") or item.get("key") or default_label
                text = item.get("text") or item.get("value") or item.get("content") or item
                choices.append(f"{normalize_text(label)}. {normalize_text(text)}")
            else:
                text = normalize_text(item)
                if re.match(r"^[A-Z]\.", text):
                    choices.append(text)
                elif text:
                    choices.append(f"{default_label}. {text}")
        return choices
    text = normalize_text(value)
    return [text] if text else []


def _jsonable(value: Any) -> Any:
    try:
        json.dumps(value, ensure_ascii=False)
        return value
    except TypeError:
        return str(value)


def compact_metadata(raw: dict, allowed_keys: list[str], max_value_chars: int = 500) -> dict:
    metadata: dict[str, Any] = {}
    for key in allowed_keys:
        if key not in raw:
            continue
        value = _jsonable(raw[key])
        if isinstance(value, str) and len(value) > max_value_chars:
            value = value[:max_value_chars] + "...[truncated]"
        elif not isinstance(value, (str, int, float, bool, type(None))):
            rendered = json.dumps(value, ensure_ascii=False, sort_keys=True)
            if len(rendered) > max_value_chars:
                rendered = rendered[:max_value_chars] + "...[truncated]"
            value = json.loads(rendered) if rendered.endswith("...[truncated]") is False else rendered
        metadata[key] = value
    return metadata


def make_public_task_id(dataset: str, split: str, index: int) -> str:
    return f"{dataset}_{split}_{index:05d}"
