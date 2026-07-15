"""Tests for the Claude renderer."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from kedro_skills.installer import FileRecord, compute_sha256
from kedro_skills.registry import SkillMetadata
from kedro_skills.renderers.claude import render

if TYPE_CHECKING:
    from pathlib import Path

SKILL = SkillMetadata(
    id="catalog-config",
    category="data",
    description="Kedro data catalog configuration guidance",
    paths=["conf/**/*.yml", "conf/**/*.yaml"],
    ide_support=["claude"],
)

VALID_SKILL_MD = """\
---
name: catalog-config
description: >
  Kedro data catalog configuration guidance.
paths:
  - "conf/**/*.yml"
  - "conf/**/*.yaml"
---

# Catalog Configuration

Help the user write correct Kedro data catalog entries.
"""

NO_PATHS_SKILL_MD = """\
---
name: catalog-config
description: Kedro data catalog configuration guidance.
---

# Catalog Configuration

Missing the paths frontmatter.
"""


def _write_canonical(tmp_path: Path, content: str = VALID_SKILL_MD) -> Path:
    canonical = tmp_path / ".agents" / "skills" / "catalog-config" / "SKILL.md"
    canonical.parent.mkdir(parents=True, exist_ok=True)
    canonical.write_text(content)
    return canonical


class TestRender:
    def test_creates_claude_copy(self, tmp_path: Path) -> None:
        _write_canonical(tmp_path)
        render(SKILL, tmp_path)
        assert (tmp_path / ".claude/skills/catalog-config/SKILL.md").is_file()

    def test_byte_identical_copy(self, tmp_path: Path) -> None:
        canonical = _write_canonical(tmp_path)
        render(SKILL, tmp_path)
        original = canonical.read_bytes()
        copy = (tmp_path / ".claude/skills/catalog-config/SKILL.md").read_bytes()
        assert copy == original

    def test_sha256_matches_canonical(self, tmp_path: Path) -> None:
        canonical = _write_canonical(tmp_path)
        records = render(SKILL, tmp_path)
        assert records[0].sha256 == compute_sha256(canonical)

    def test_returns_file_record(self, tmp_path: Path) -> None:
        _write_canonical(tmp_path)
        records = render(SKILL, tmp_path)
        assert len(records) == 1
        rec = records[0]
        assert isinstance(rec, FileRecord)
        assert rec.path == ".claude/skills/catalog-config/SKILL.md"
        assert rec.kind == "managed_copy"
        assert rec.block_id is None
        assert len(rec.sha256) == 64


class TestErrorCases:
    def test_error_when_canonical_missing(self, tmp_path: Path) -> None:
        with pytest.raises(FileNotFoundError, match="Canonical SKILL.md not found"):
            render(SKILL, tmp_path)

    def test_error_when_paths_frontmatter_missing(self, tmp_path: Path) -> None:
        _write_canonical(tmp_path, NO_PATHS_SKILL_MD)
        with pytest.raises(ValueError, match="missing 'paths:' frontmatter"):
            render(SKILL, tmp_path)


class TestIdempotency:
    def test_render_twice_same_result(self, tmp_path: Path) -> None:
        _write_canonical(tmp_path)
        r1 = render(SKILL, tmp_path)
        content1 = (tmp_path / ".claude/skills/catalog-config/SKILL.md").read_bytes()
        r2 = render(SKILL, tmp_path)
        content2 = (tmp_path / ".claude/skills/catalog-config/SKILL.md").read_bytes()
        assert r1 == r2
        assert content1 == content2
