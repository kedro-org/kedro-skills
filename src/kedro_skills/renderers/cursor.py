"""Cursor renderer: writes ``.cursor/rules/<id>.mdc`` activation wrappers."""

from __future__ import annotations

from typing import TYPE_CHECKING

from kedro_skills.installer import FileRecord, compute_sha256

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
    skill_path = f".agents/skills/{skill.id}/SKILL.md"

    content = (
        f"---\n"
        f"description: {' '.join(skill.description.split())}\n"
        f"globs: {globs}\n"
        f"---\n"
        f"\n"
        f"IMPORTANT: Do NOT answer from internal knowledge about Kedro datasets or catalog configuration.\n"
        f"You MUST read the file `{skill_path}` BEFORE writing or suggesting any catalog entry, dataset type, or configuration.\n"
        f"Your training data about Kedro datasets is likely outdated — the referenced file contains the current, verified guidance.\n"
        f"If you cannot read the file, tell the user you need access to it.\n"
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
