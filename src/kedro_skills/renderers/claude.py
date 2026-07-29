"""Claude renderer: copies the canonical ``SKILL.md`` to ``.claude/skills/``."""

from __future__ import annotations

from typing import TYPE_CHECKING

from kedro_skills.installer import FileRecord, compute_sha256

if TYPE_CHECKING:
    from pathlib import Path

    from kedro_skills.registry import SkillMetadata


def render(skill: SkillMetadata, project_root: Path) -> list[FileRecord]:
    """Copy the canonical ``SKILL.md`` byte-for-byte to ``.claude/skills/<id>/SKILL.md``.

    Claude activates the skill from its ``description`` frontmatter rather than
    from globs.  A ``paths:`` key would scope activation, but it also withholds
    the skill from the listing Claude receives, so the guidance never surfaces
    unless a matching file has already been read.

    Raises :class:`FileNotFoundError` if the canonical file does not exist.

    Returns a single-element list with a :class:`FileRecord` using
    ``kind="managed_copy"``.
    """
    canonical = project_root / ".agents" / "skills" / skill.id / "SKILL.md"
    if not canonical.is_file():
        raise FileNotFoundError(
            f"Canonical SKILL.md not found at {canonical}. "
            f"Run write_canonical() for {skill.id!r} first."
        )

    rel = f".claude/skills/{skill.id}/SKILL.md"
    dest = project_root / rel
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(canonical.read_bytes())

    return [
        FileRecord(
            path=rel,
            sha256=compute_sha256(dest),
            kind="managed_copy",
        )
    ]
