"""Tests for the Cursor renderer."""

from __future__ import annotations

from typing import TYPE_CHECKING

from kedro_skills.installer import FileRecord, compute_sha256
from kedro_skills.registry import SkillMetadata
from kedro_skills.renderers.cursor import render

if TYPE_CHECKING:
    from pathlib import Path

SKILL = SkillMetadata(
    id="catalog-config",
    category="data",
    description="Kedro data catalog configuration guidance",
    paths=["conf/**/*.yml", "conf/**/*.yaml"],
    ide_support=["cursor"],
)

EXPECTED_CONTENT = """\
---
description: Kedro data catalog configuration guidance
globs: conf/**/*.yml, conf/**/*.yaml
---

When editing files matching these patterns, read `.agents/skills/catalog-config/SKILL.md` and follow its guidelines.
"""


class TestRender:
    def test_creates_mdc_file(self, tmp_path: Path) -> None:
        render(SKILL, tmp_path)
        assert (tmp_path / ".cursor" / "rules" / "catalog-config.mdc").is_file()

    def test_creates_directory_structure(self, tmp_path: Path) -> None:
        render(SKILL, tmp_path)
        assert (tmp_path / ".cursor" / "rules").is_dir()

    def test_golden_file_content(self, tmp_path: Path) -> None:
        render(SKILL, tmp_path)
        actual = (tmp_path / ".cursor/rules/catalog-config.mdc").read_text()
        assert actual == EXPECTED_CONTENT

    def test_returns_file_record(self, tmp_path: Path) -> None:
        records = render(SKILL, tmp_path)
        assert len(records) == 1
        rec = records[0]
        assert isinstance(rec, FileRecord)
        assert rec.path == ".cursor/rules/catalog-config.mdc"
        assert rec.kind == "activation_wrapper"
        assert rec.block_id is None
        assert len(rec.sha256) == 64

    def test_sha256_matches_file(self, tmp_path: Path) -> None:
        records = render(SKILL, tmp_path)
        dest = tmp_path / records[0].path
        assert records[0].sha256 == compute_sha256(dest)

    def test_globs_are_comma_separated(self, tmp_path: Path) -> None:
        render(SKILL, tmp_path)
        content = (tmp_path / ".cursor/rules/catalog-config.mdc").read_text()
        assert "globs: conf/**/*.yml, conf/**/*.yaml" in content


class TestMultilineDescription:
    def test_description_is_single_line(self, tmp_path: Path) -> None:
        skill = SkillMetadata(
            id="catalog-config",
            category="data",
            description="Line one.\nLine two.\n  Extra spaces.",
            paths=["conf/**/*.yml"],
            ide_support=["cursor"],
        )
        render(skill, tmp_path)
        content = (tmp_path / ".cursor/rules/catalog-config.mdc").read_text()
        for line in content.splitlines():
            if line.startswith("description:"):
                assert "\n" not in line
                assert "Line one. Line two. Extra spaces." in line
                break
        else:
            raise AssertionError("description: line not found")


class TestIdempotency:
    def test_render_twice_same_result(self, tmp_path: Path) -> None:
        r1 = render(SKILL, tmp_path)
        content1 = (tmp_path / ".cursor/rules/catalog-config.mdc").read_text()
        r2 = render(SKILL, tmp_path)
        content2 = (tmp_path / ".cursor/rules/catalog-config.mdc").read_text()
        assert r1 == r2
        assert content1 == content2
