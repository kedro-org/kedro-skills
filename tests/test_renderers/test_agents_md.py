"""Tests for the AGENTS.md renderer."""

from __future__ import annotations

import hashlib
from typing import TYPE_CHECKING

from kedro_skills.installer import FileRecord
from kedro_skills.registry import SkillMetadata
from kedro_skills.renderers.agents_md import _make_block, render

if TYPE_CHECKING:
    from pathlib import Path

SKILL = SkillMetadata(
    id="catalog-config",
    category="data",
    description="Kedro data catalog configuration guidance",
    paths=["conf/**/*.yml", "conf/**/*.yaml"],
    ide_support=["cursor", "copilot", "claude"],
)


class TestRenderNoExistingFile:
    def test_creates_agents_md(self, tmp_path: Path) -> None:
        render(SKILL, tmp_path)
        assert (tmp_path / "AGENTS.md").is_file()

    def test_contains_header(self, tmp_path: Path) -> None:
        render(SKILL, tmp_path)
        content = (tmp_path / "AGENTS.md").read_text()
        assert "# Agent Guidelines" in content
        assert "Kedro" in content

    def test_contains_skill_block(self, tmp_path: Path) -> None:
        render(SKILL, tmp_path)
        content = (tmp_path / "AGENTS.md").read_text()
        assert "<!-- kedro-skills:catalog-config:start -->" in content
        assert "<!-- kedro-skills:catalog-config:end -->" in content
        assert ".agents/skills/catalog-config/SKILL.md" in content

    def test_returns_file_record(self, tmp_path: Path) -> None:
        records = render(SKILL, tmp_path)
        assert len(records) == 1
        rec = records[0]
        assert isinstance(rec, FileRecord)
        assert rec.path == "AGENTS.md"
        assert rec.kind == "agents_md_block"
        assert rec.block_id == "kedro-skills:catalog-config"
        assert len(rec.sha256) == 64

    def test_sha256_covers_block_only(self, tmp_path: Path) -> None:
        records = render(SKILL, tmp_path)
        block = _make_block(SKILL)
        expected = hashlib.sha256(block.encode("utf-8")).hexdigest()
        assert records[0].sha256 == expected


class TestRenderExistingFileNoBlock:
    def test_preserves_existing_content(self, tmp_path: Path) -> None:
        existing = "# My Custom Guidelines\n\nSome user content here.\n"
        (tmp_path / "AGENTS.md").write_text(existing)
        render(SKILL, tmp_path)
        content = (tmp_path / "AGENTS.md").read_text()
        assert "# My Custom Guidelines" in content
        assert "Some user content here." in content
        assert "<!-- kedro-skills:catalog-config:start -->" in content

    def test_appends_block(self, tmp_path: Path) -> None:
        existing = "# Existing Header\n"
        (tmp_path / "AGENTS.md").write_text(existing)
        render(SKILL, tmp_path)
        content = (tmp_path / "AGENTS.md").read_text()
        header_pos = content.index("# Existing Header")
        block_pos = content.index("<!-- kedro-skills:catalog-config:start -->")
        assert block_pos > header_pos


class TestRenderExistingFileWithOutdatedBlock:
    def test_replaces_block_in_place(self, tmp_path: Path) -> None:
        old_block = (
            "<!-- kedro-skills:catalog-config:start -->\n"
            "## Old Content\n"
            "This is outdated.\n"
            "<!-- kedro-skills:catalog-config:end -->"
        )
        existing = f"# Header\n\nBefore block.\n\n{old_block}\n\nAfter block.\n"
        (tmp_path / "AGENTS.md").write_text(existing)
        render(SKILL, tmp_path)
        content = (tmp_path / "AGENTS.md").read_text()
        assert "Old Content" not in content
        assert "This is outdated." not in content
        assert "## Catalog config" in content
        assert "Before block." in content
        assert "After block." in content

    def test_preserves_content_outside_markers(self, tmp_path: Path) -> None:
        old_block = (
            "<!-- kedro-skills:catalog-config:start -->\n"
            "Old.\n"
            "<!-- kedro-skills:catalog-config:end -->"
        )
        existing = (
            "# My Guidelines\n\n"
            "Custom intro.\n\n"
            f"{old_block}\n\n"
            "## My Custom Section\n\n"
            "User-written content that must be preserved.\n"
        )
        (tmp_path / "AGENTS.md").write_text(existing)
        render(SKILL, tmp_path)
        content = (tmp_path / "AGENTS.md").read_text()
        assert "# My Guidelines" in content
        assert "Custom intro." in content
        assert "## My Custom Section" in content
        assert "User-written content that must be preserved." in content


SKILL_B = SkillMetadata(
    id="pipeline-config",
    category="pipelines",
    description="Kedro pipeline configuration guidance",
    paths=["src/**/*.py"],
    ide_support=["cursor"],
)


class TestMultipleSkills:
    def test_two_skills_coexist(self, tmp_path: Path) -> None:
        render(SKILL, tmp_path)
        render(SKILL_B, tmp_path)
        content = (tmp_path / "AGENTS.md").read_text()
        assert "<!-- kedro-skills:catalog-config:start -->" in content
        assert "<!-- kedro-skills:catalog-config:end -->" in content
        assert "<!-- kedro-skills:pipeline-config:start -->" in content
        assert "<!-- kedro-skills:pipeline-config:end -->" in content

    def test_updating_one_preserves_the_other(self, tmp_path: Path) -> None:
        render(SKILL, tmp_path)
        render(SKILL_B, tmp_path)
        render(SKILL, tmp_path)
        content = (tmp_path / "AGENTS.md").read_text()
        assert content.count("<!-- kedro-skills:catalog-config:start -->") == 1
        assert "<!-- kedro-skills:pipeline-config:start -->" in content


class TestIdempotency:
    def test_render_twice_same_result(self, tmp_path: Path) -> None:
        r1 = render(SKILL, tmp_path)
        content1 = (tmp_path / "AGENTS.md").read_text()
        r2 = render(SKILL, tmp_path)
        content2 = (tmp_path / "AGENTS.md").read_text()
        assert r1 == r2
        assert content1 == content2

    def test_render_twice_existing_file(self, tmp_path: Path) -> None:
        (tmp_path / "AGENTS.md").write_text("# Existing\n")
        r1 = render(SKILL, tmp_path)
        content1 = (tmp_path / "AGENTS.md").read_text()
        r2 = render(SKILL, tmp_path)
        content2 = (tmp_path / "AGENTS.md").read_text()
        assert r1 == r2
        assert content1 == content2
