"""Copilot renderer: writes ``.github/instructions/<id>.instructions.md``."""

from __future__ import annotations

from typing import TYPE_CHECKING

from kedro_skills.installer import FileRecord, compute_sha256
from kedro_skills.renderers._pointer import pointer_body

if TYPE_CHECKING:
    from pathlib import Path

    from kedro_skills.registry import SkillMetadata


def render(skill: SkillMetadata, project_root: Path) -> list[FileRecord]:
    """Write a ``.github/instructions/<id>.instructions.md`` file for *skill*.

    The file contains ``description:`` and ``applyTo:`` frontmatter plus a body
    that instructs the agent to read the canonical ``SKILL.md`` before
    answering.  ``description`` is what drives Copilot's task-relevance
    matching when no ``applyTo`` glob is in context, so it is not optional.

    Returns a single-element list with a :class:`FileRecord` using
    ``kind="activation_wrapper"``.
    """
    apply_to = ", ".join(skill.paths)

    content = (
        f"---\n"
        f"description: {' '.join(skill.description.split())}\n"
        f"applyTo: {apply_to}\n"
        f"---\n"
        f"\n"
        f"{pointer_body(skill.id, skill.paths)}"
    )

    rel = f".github/instructions/{skill.id}.instructions.md"
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
