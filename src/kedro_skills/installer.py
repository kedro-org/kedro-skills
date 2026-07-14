"""Canonical writer: copies a packaged ``SKILL.md`` into a Kedro project."""

from __future__ import annotations

import hashlib
import importlib.resources
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from kedro_skills.registry import SkillMetadata


@dataclass(frozen=True)
class FileRecord:
    """A file written by the installer, together with its content hash."""

    path: str
    sha256: str


def compute_sha256(path: Path) -> str:
    """Return the hex-encoded SHA-256 digest of *path*."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def _resolve_skill_path(skill_id: str) -> Path:
    """Locate the packaged ``SKILL.md`` for *skill_id*.

    Works both from an installed wheel (``force-include`` puts ``skills/``
    inside the package) and from an editable install (``skills/`` lives at
    the repository root, two levels above ``src/kedro_skills/``).
    """
    pkg = importlib.resources.files("kedro_skills")
    wheel_path = Path(str(pkg / "skills" / skill_id / "SKILL.md"))
    if wheel_path.is_file():
        return wheel_path

    dev_path = Path(str(pkg)).parent.parent / "skills" / skill_id / "SKILL.md"
    if dev_path.is_file():
        return dev_path

    raise FileNotFoundError(
        f"Cannot locate SKILL.md for {skill_id!r}. "
        f"Searched:\n  {wheel_path}\n  {dev_path}"
    )


def write_canonical(skill: SkillMetadata, project_root: Path) -> FileRecord:
    """Copy the packaged ``SKILL.md`` to the project's canonical location.

    Writes to ``<project_root>/.agents/skills/<id>/SKILL.md`` and returns
    a :class:`FileRecord` with the relative path and SHA-256 digest.

    Pure — does **not** touch ``.installed.json``.
    """
    source = _resolve_skill_path(skill.id)
    content = source.read_bytes()

    rel = Path(".agents", "skills", skill.id, "SKILL.md")
    dest = project_root / rel
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(content)

    return FileRecord(path=str(rel), sha256=compute_sha256(dest))
