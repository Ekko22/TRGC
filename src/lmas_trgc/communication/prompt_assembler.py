from __future__ import annotations


def _item_content(item) -> str:
    if isinstance(item, dict):
        return str(item.get("content", ""))
    return str(item)


def _render_block(title: str, items: list) -> str:
    body = "\n".join(f"- {_item_content(item)}" for item in items) if items else "(none)"
    return f"## {title}\n{body}"


def assemble_receiver_context(
    trusted_messages: list,
    warning_messages: list,
    untrusted_messages: list,
    notices: list,
) -> str:
    return "\n\n".join(
        [
            _render_block("Trusted messages", trusted_messages),
            _render_block("Risk-marked messages", warning_messages),
            _render_block("Untrusted notes", untrusted_messages),
            _render_block("Safety notices", notices),
        ]
    )
