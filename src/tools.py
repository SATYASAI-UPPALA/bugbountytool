from __future__ import annotations

import shlex
import subprocess
from dataclasses import dataclass

from .config import settings


BLOCKED_TOKENS = {
    "rm",
    "mkfs",
    "shutdown",
    "reboot",
    "halt",
    "poweroff",
    ":(){",
}


@dataclass
class CommandResult:
    command: str
    exit_code: int
    stdout: str
    stderr: str
    dry_run: bool

    def format_for_model(self) -> str:
        return (
            f"$ {self.command}\n"
            f"exit_code={self.exit_code} dry_run={self.dry_run}\n"
            f"stdout:\n{self.stdout.strip() or '<empty>'}\n"
            f"stderr:\n{self.stderr.strip() or '<empty>'}"
        )


def validate_command(command: str) -> None:
    lowered = command.lower()
    if any(token in lowered for token in BLOCKED_TOKENS):
        raise ValueError(f"Blocked unsafe command token in: {command}")

    try:
        parts = shlex.split(command)
    except ValueError as exc:
        raise ValueError(f"Invalid shell command: {exc}") from exc

    if not parts:
        raise ValueError("Command cannot be empty.")


def run_kali_command(command: str) -> CommandResult:
    validate_command(command)

    if settings.dry_run:
        return CommandResult(
            command=command,
            exit_code=0,
            stdout="[dry-run] Command was not executed.",
            stderr="",
            dry_run=True,
        )

    completed = subprocess.run(
        command,
        cwd=settings.workdir,
        shell=True,
        capture_output=True,
        text=True,
        timeout=settings.timeout_seconds,
        check=False,
    )
    return CommandResult(
        command=command,
        exit_code=completed.returncode,
        stdout=completed.stdout[-8000:],
        stderr=completed.stderr[-8000:],
        dry_run=False,
    )
