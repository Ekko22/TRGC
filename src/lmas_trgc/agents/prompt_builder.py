from __future__ import annotations


def build_role_prompt(role: str, task_text: str, context: str = "") -> str:
    return f"Role: {role}\nTask: {task_text}\nContext:\n{context}".strip()
