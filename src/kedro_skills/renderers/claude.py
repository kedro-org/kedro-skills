"""Claude renderer: copies the canonical ``SKILL.md`` to ``.claude/skills/``."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

from kedro_skills.installer import FileRecord, compute_sha256

if TYPE_CHECKING:
    from pathlib import Path

    from kedro_skills.registry import SkillMetadata

_PATHS_RE = re.compile(r"^paths:\s*$", re.MULTILINE)


def _has_paths_frontmatter(text: str) -> bool:
    """Return ``True`` if *text* contains a ``paths:`` key in YAML frontmatter.

    Only searches between the ``---`` delimiters, so a ``paths:`` string
    appearing in the Markdown body does not produce a false positive.
    """
    if not text.startswith("---"):
        return False
    end = text.find("---", 3)
    if end == -1:
        return False
    frontmatter = text[: end + 3]
    return bool(_PATHS_RE.search(frontmatter))


def render(skill: SkillMetadata, project_root: Path) -> list[FileRecord]:
    """Copy the canonical ``SKILL.md`` byte-for-byte to ``.claude/skills/<id>/SKILL.md``.

    Claude uses the ``paths:`` frontmatter in ``SKILL.md`` for native glob
    activation, so this renderer verifies that the source file contains it.

    Raises :class:`FileNotFoundError` if the canonical file does not exist
    and :class:`ValueError` if the ``paths:`` frontmatter is missing.

    Returns a single-element list with a :class:`FileRecord` using
    ``kind="managed_copy"``.
    """
    canonical = project_root / ".agents" / "skills" / skill.id / "SKILL.md"
    if not canonical.is_file():
        raise FileNotFoundError(
            f"Canonical SKILL.md not found at {canonical}. "
            f"Run write_canonical() for {skill.id!r} first."
        )

    source_bytes = canonical.read_bytes()
    if not _has_paths_frontmatter(source_bytes.decode("utf-8")):
        raise ValueError(
            f"Canonical SKILL.md for {skill.id!r} is missing 'paths:' "
            f"frontmatter, which Claude requires for glob activation."
        )

    rel = f".claude/skills/{skill.id}/SKILL.md"
    dest = project_root / rel
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(source_bytes)

    return [
        FileRecord(
            path=rel,
            sha256=compute_sha256(dest),
            kind="managed_copy",
        )
    ]
