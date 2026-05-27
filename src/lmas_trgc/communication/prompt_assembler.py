from __future__ import annotations


def _render_block(title: str, items: list[str]) -> str:
    body = "\n".join(f"- {item}" for item in items) if items else "- None"
    return f"## {title}\n{body}"


def assemble_receiver_context(
    trusted_messages: list[str],
    warning_messages: list[str],
    untrusted_messages: list[str],
    notices: list[str],
) -> str:
    return "\n\n".join(
        [
            _render_block("Trusted messages", trusted_messages),
            _render_block("Risk-marked messages", warning_messages),
            _render_block("Untrusted notes", untrusted_messages),
            _render_block("Safety notices", notices),
        ]
    )
