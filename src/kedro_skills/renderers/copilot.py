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

    File-scoped skills use ``applyTo:``. Skills without paths omit that field
    and use ``description`` for on-demand discovery. Both point to the
    canonical ``SKILL.md``.

    Returns a single-element list with a :class:`FileRecord` using
    ``kind="activation_wrapper"``.
    """
    scope = f"applyTo: {', '.join(skill.paths)}\n" if skill.paths else ""

    content = (
        f"---\n"
        f"description: {' '.join(skill.description.split())}\n"
        f"{scope}"
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
