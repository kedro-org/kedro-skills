from __future__ import annotations

import hashlib
from typing import TYPE_CHECKING

from kedro_skills.installer import (
    FileRecord,
    _resolve_skill_path,
    compute_sha256,
    write_canonical,
)
from kedro_skills.registry import SkillMetadata

if TYPE_CHECKING:
    from pathlib import Path


SKILL = SkillMetadata(
    id="catalog-config",
    category="data",
    description="Catalog guidance",
    paths=["conf/**/*.yml"],
    ide_support=["cursor"],
)


class TestComputeSha256:
    def test_known_content(self, tmp_path: Path) -> None:
        p = tmp_path / "hello.txt"
        p.write_text("hello")
        expected = hashlib.sha256(b"hello").hexdigest()
        assert compute_sha256(p) == expected

    def test_binary_content(self, tmp_path: Path) -> None:
        p = tmp_path / "bin"
        data = bytes(range(256))
        p.write_bytes(data)
        expected = hashlib.sha256(data).hexdigest()
        assert compute_sha256(p) == expected


class TestWriteCanonical:
    def test_produces_correct_path(self, tmp_path: Path) -> None:
        record = write_canonical(SKILL, tmp_path)
        expected_path = ".agents/skills/catalog-config/SKILL.md"
        assert record.path == expected_path
        assert (tmp_path / expected_path).exists()

    def test_content_is_byte_identical(self, tmp_path: Path) -> None:
        write_canonical(SKILL, tmp_path)
        written = (tmp_path / ".agents/skills/catalog-config/SKILL.md").read_bytes()

        original = _resolve_skill_path("catalog-config").read_bytes()
        assert written == original

    def test_sha256_is_valid(self, tmp_path: Path) -> None:
        record = write_canonical(SKILL, tmp_path)
        dest = tmp_path / record.path
        expected = hashlib.sha256(dest.read_bytes()).hexdigest()
        assert record.sha256 == expected

    def test_returns_file_record(self, tmp_path: Path) -> None:
        record = write_canonical(SKILL, tmp_path)
        assert isinstance(record, FileRecord)
        assert isinstance(record.path, str)
        assert len(record.sha256) == 64  # hex SHA-256

    def test_idempotent(self, tmp_path: Path) -> None:
        r1 = write_canonical(SKILL, tmp_path)
        r2 = write_canonical(SKILL, tmp_path)
        assert r1 == r2
        content = (tmp_path / r1.path).read_bytes()
        assert hashlib.sha256(content).hexdigest() == r1.sha256

    def test_creates_parent_directories(self, tmp_path: Path) -> None:
        project = tmp_path / "deep" / "nested" / "project"
        project.mkdir(parents=True)
        record = write_canonical(SKILL, project)
        assert (project / record.path).exists()
