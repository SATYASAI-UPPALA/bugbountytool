from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ModelDecision:
    kind: str
    command: str | None = None
    reason: str | None = None
    final: str | None = None


def parse_decision(text: str) -> ModelDecision:
    stripped = text.strip()
    if stripped.startswith("FINAL:"):
        return ModelDecision(kind="final", final=stripped.removeprefix("FINAL:").strip())

    if not stripped.startswith("ACTION:"):
        return ModelDecision(
            kind="final",
            final=f"Model returned an unrecognized response format:\n\n{stripped}",
        )

    body = stripped.removeprefix("ACTION:").strip()
    command, _, reason = body.partition("REASON:")
    return ModelDecision(
        kind="action",
        command=command.strip(),
        reason=reason.strip() or None,
    )
