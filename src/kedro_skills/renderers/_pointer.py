"""Shared text pointing an agent at the canonical ``SKILL.md``."""

from __future__ import annotations

from typing import TYPE_CHECKING

from kedro_skills.installer import _resolve_skill_path

if TYPE_CHECKING:
    from collections.abc import Sequence


def skill_path(skill_id: str) -> str:
    """Return the project-relative path to the canonical ``SKILL.md``."""
    return f".agents/skills/{skill_id}/SKILL.md"


def _bundled_note(skill_id: str) -> str:
    """Tell the agent where a skill's extra files live, if it has any."""
    try:
        has_files = any(
            p.is_file() and p.name != "SKILL.md" and "__pycache__" not in p.parts
            for p in _resolve_skill_path(skill_id).parent.rglob("*")
        )
    except FileNotFoundError:
        has_files = False
    if not has_files:
        return ""
    return (
        "The skill ships extra files (rules, scripts). Paths it names are "
        f"relative to `.agents/skills/{skill_id}/`, not the project root.\n"
    )


def pointer_body(skill_id: str, paths: Sequence[str]) -> str:
    """Return the instruction directing an agent to read *skill_id*'s guidance.

    The wording is deliberately forceful: a mildly-worded reference gets
    ignored, and the agent answers from stale training data without ever
    opening the file.

    File-scoped skills name *paths* explicitly because ``AGENTS.md`` is loaded
    for every task. Skills without paths apply only to matching requests.
    """
    extra_files_note = _bundled_note(skill_id)
    if not paths:
        return (
            "IMPORTANT: Use this skill only when the user's request matches "
            "its description.\n"
            f"You MUST read `{skill_path(skill_id)}` BEFORE planning, answering, "
            "or working on that request.\n"
            "Do not load it solely because a file is being edited.\n"
            "If you cannot read the file, tell the user instead of guessing.\n"
            f"{extra_files_note}"
        )

    globs = ", ".join(f"`{p}`" for p in paths)
    return (
        f"IMPORTANT: When working on files matching {globs}, do NOT answer "
        "from internal knowledge.\n"
        f"You MUST read `{skill_path(skill_id)}` BEFORE writing, editing, or "
        "suggesting changes to them.\n"
        "Your training data is likely outdated — that file holds the current, "
        "verified guidance.\n"
        "If you cannot read the file, tell the user instead of guessing.\n"
        f"{extra_files_note}"
    )
