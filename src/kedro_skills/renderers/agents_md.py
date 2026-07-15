"""AGENTS.md renderer: manages skill blocks in the project's ``AGENTS.md``."""

from __future__ import annotations

import hashlib
import re
from typing import TYPE_CHECKING

from kedro_skills.installer import FileRecord

if TYPE_CHECKING:
    from pathlib import Path

    from kedro_skills.registry import SkillMetadata

_HEADER = """\
# Agent Guidelines

This is a [Kedro](https://docs.kedro.org) project. \
These guidelines help AI coding assistants work with it correctly.
"""


def _block_id(skill_id: str) -> str:
    return f"kedro-skills:{skill_id}"


def _start_marker(skill_id: str) -> str:
    return f"<!-- {_block_id(skill_id)}:start -->"


def _end_marker(skill_id: str) -> str:
    return f"<!-- {_block_id(skill_id)}:end -->"


def _make_block(skill: SkillMetadata) -> str:
    """Build the managed block for *skill* (markers inclusive)."""
    heading = skill.id.replace("-", " ").replace("_", " ").capitalize()
    skill_path = f".agents/skills/{skill.id}/SKILL.md"
    paths_str = ", ".join(f"`{p}`" for p in skill.paths)

    return (
        f"{_start_marker(skill.id)}\n"
        f"## {heading}\n"
        f"\n"
        f"{skill.description}\n"
        f"\n"
        f"When editing files matching {paths_str}, "
        f"read [{skill_path}]({skill_path}) for detailed guidance.\n"
        f"{_end_marker(skill.id)}"
    )


def _sha256_of(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def render(skill: SkillMetadata, project_root: Path) -> list[FileRecord]:
    """Render or update the managed block for *skill* in ``AGENTS.md``.

    Returns a single-element list with a :class:`FileRecord` whose SHA-256
    covers only the managed block (markers inclusive), not the whole file.
    """
    agents_md = project_root / "AGENTS.md"
    block = _make_block(skill)
    bid = _block_id(skill.id)

    start = _start_marker(skill.id)
    end = _end_marker(skill.id)

    if agents_md.is_file():
        content = agents_md.read_text(encoding="utf-8")
        pattern = re.compile(
            re.escape(start) + r".*?" + re.escape(end),
            re.DOTALL,
        )
        if pattern.search(content):
            content = pattern.sub(block, content)
        else:
            if not content.endswith("\n"):
                content += "\n"
            content += "\n" + block + "\n"
    else:
        content = _HEADER + "\n" + block + "\n"

    agents_md.write_text(content, encoding="utf-8")

    return [
        FileRecord(
            path="AGENTS.md",
            sha256=_sha256_of(block),
            kind="agents_md_block",
            block_id=bid,
        )
    ]
