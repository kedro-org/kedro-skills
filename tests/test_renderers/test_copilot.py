"""Tests for the Copilot renderer."""

from __future__ import annotations

from typing import TYPE_CHECKING

from kedro_skills.installer import FileRecord, compute_sha256
from kedro_skills.registry import SkillMetadata
from kedro_skills.renderers.copilot import render

if TYPE_CHECKING:
    from pathlib import Path

SKILL = SkillMetadata(
    id="catalog-config",
    category="data",
    description="Kedro data catalog configuration guidance",
    paths=["conf/**/*.yml", "conf/**/*.yaml"],
    ide_support=["copilot"],
)

EXPECTED_CONTENT = """\
---
applyTo: conf/**/*.yml, conf/**/*.yaml
---

When editing files matching these patterns, read `.agents/skills/catalog-config/SKILL.md` and follow its guidelines.
"""


class TestRender:
    def test_creates_instructions_file(self, tmp_path: Path) -> None:
        render(SKILL, tmp_path)
        assert (
            tmp_path / ".github/instructions/catalog-config.instructions.md"
        ).is_file()

    def test_creates_directory_structure(self, tmp_path: Path) -> None:
        render(SKILL, tmp_path)
        assert (tmp_path / ".github" / "instructions").is_dir()

    def test_golden_file_content(self, tmp_path: Path) -> None:
        render(SKILL, tmp_path)
        actual = (
            tmp_path / ".github/instructions/catalog-config.instructions.md"
        ).read_text()
        assert actual == EXPECTED_CONTENT

    def test_returns_file_record(self, tmp_path: Path) -> None:
        records = render(SKILL, tmp_path)
        assert len(records) == 1
        rec = records[0]
        assert isinstance(rec, FileRecord)
        assert rec.path == ".github/instructions/catalog-config.instructions.md"
        assert rec.kind == "activation_wrapper"
        assert rec.block_id is None
        assert len(rec.sha256) == 64

    def test_sha256_matches_file(self, tmp_path: Path) -> None:
        records = render(SKILL, tmp_path)
        dest = tmp_path / records[0].path
        assert records[0].sha256 == compute_sha256(dest)

    def test_apply_to_is_comma_separated(self, tmp_path: Path) -> None:
        render(SKILL, tmp_path)
        content = (
            tmp_path / ".github/instructions/catalog-config.instructions.md"
        ).read_text()
        assert "applyTo: conf/**/*.yml, conf/**/*.yaml" in content


class TestIdempotency:
    def test_render_twice_same_result(self, tmp_path: Path) -> None:
        rel = ".github/instructions/catalog-config.instructions.md"
        r1 = render(SKILL, tmp_path)
        content1 = (tmp_path / rel).read_text()
        r2 = render(SKILL, tmp_path)
        content2 = (tmp_path / rel).read_text()
        assert r1 == r2
        assert content1 == content2
