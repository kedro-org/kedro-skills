"""Shared text pointing an agent at the canonical ``SKILL.md``."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Sequence


def skill_path(skill_id: str) -> str:
    """Return the project-relative path to the canonical ``SKILL.md``."""
    return f".agents/skills/{skill_id}/SKILL.md"


def pointer_body(skill_id: str, paths: Sequence[str]) -> str:
    """Return the instruction directing an agent to read *skill_id*'s guidance.

    The wording is deliberately forceful: a mildly-worded reference gets
    ignored, and the agent answers from stale training data without ever
    opening the file.

    It names *paths* rather than relying on surrounding context, because the
    text has to stand alone in ``AGENTS.md``, which is loaded for every task
    rather than scoped to matching files.
    """
    globs = ", ".join(f"`{p}`" for p in paths)
    return (
        f"IMPORTANT: When working on files matching {globs}, do NOT answer "
        "from internal knowledge.\n"
        f"You MUST read `{skill_path(skill_id)}` BEFORE writing, editing, or "
        "suggesting changes to them.\n"
        "Your training data is likely outdated — that file holds the current, "
        "verified guidance.\n"
        "If you cannot read the file, tell the user instead of guessing.\n"
    )
