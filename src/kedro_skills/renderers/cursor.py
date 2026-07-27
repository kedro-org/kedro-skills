"""Cursor renderer: writes ``.cursor/rules/<id>.mdc`` activation wrappers."""

from __future__ import annotations

from typing import TYPE_CHECKING

from kedro_skills.installer import FileRecord, compute_sha256
from kedro_skills.renderers._pointer import pointer_body

if TYPE_CHECKING:
    from pathlib import Path

    from kedro_skills.registry import SkillMetadata


def render(skill: SkillMetadata, project_root: Path) -> list[FileRecord]:
    """Write a ``.cursor/rules/<id>.mdc`` file for *skill*.

    The file contains ``description:`` and ``globs:`` frontmatter plus a
    body that forcefully instructs the agent to read the canonical
    ``SKILL.md`` before answering.

    Returns a single-element list with a :class:`FileRecord` using
    ``kind="activation_wrapper"``.
    """
    globs = ", ".join(skill.paths)

    content = (
        f"---\n"
        f"description: {' '.join(skill.description.split())}\n"
        f"globs: {globs}\n"
        f"---\n"
        f"\n"
        f"{pointer_body(skill.id, skill.paths)}"
    )

    rel = f".cursor/rules/{skill.id}.mdc"
    dest = project_root / rel
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(content, encoding="utf-8")

    return [
        FileRecord(
            path=rel,
            sha256=compute_sha256(dest),
            kind="activation_wrapper",
        )
    ]
