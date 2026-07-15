"""Copilot renderer: writes ``.github/instructions/<id>.instructions.md``."""

from __future__ import annotations

from typing import TYPE_CHECKING

from kedro_skills.installer import FileRecord, compute_sha256

if TYPE_CHECKING:
    from pathlib import Path

    from kedro_skills.registry import SkillMetadata


def render(skill: SkillMetadata, project_root: Path) -> list[FileRecord]:
    """Write a ``.github/instructions/<id>.instructions.md`` file for *skill*.

    The file contains ``applyTo:`` frontmatter plus a body that references
    the canonical ``SKILL.md``.

    Example output for ``catalog-config``::

        ---
        applyTo: conf/**/*.yml, conf/**/*.yaml
        ---

        When editing files matching these patterns, read
        `.agents/skills/catalog-config/SKILL.md` and follow its guidelines.

    Returns a single-element list with a :class:`FileRecord` using
    ``kind="activation_wrapper"``.
    """
    apply_to = ", ".join(skill.paths)
    skill_path = f".agents/skills/{skill.id}/SKILL.md"

    content = (
        f"---\n"
        f"applyTo: {apply_to}\n"
        f"---\n"
        f"\n"
        f"When editing files matching these patterns, "
        f"read `{skill_path}` and follow its guidelines.\n"
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
