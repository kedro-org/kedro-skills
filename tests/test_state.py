from __future__ import annotations

import hashlib
import json
from typing import TYPE_CHECKING

import pytest

from kedro_skills.installer import FileRecord
from kedro_skills.state import (
    DriftedFile,
    InstalledState,
    SkillState,
    detect_drift,
    read,
    write,
)

if TYPE_CHECKING:
    from pathlib import Path


def _make_state(
    skill_id: str = "catalog-config", sha: str = "abc123"
) -> InstalledState:
    return InstalledState(
        kedro_skills_version="0.1.0",
        skills={
            skill_id: SkillState(
                version="0.1.0",
                files=[
                    FileRecord(
                        path=f".agents/skills/{skill_id}/SKILL.md",
                        sha256=sha,
                    )
                ],
            )
        },
    )


class TestRoundTrip:
    def test_write_then_read(self, tmp_path: Path) -> None:
        original = _make_state()
        write(tmp_path, original)
        loaded = read(tmp_path)

        assert loaded.kedro_skills_version == original.kedro_skills_version
        assert set(loaded.skills) == set(original.skills)
        skill = loaded.skills["catalog-config"]
        assert skill.version == "0.1.0"
        assert len(skill.files) == 1
        assert skill.files[0].path == ".agents/skills/catalog-config/SKILL.md"
        assert skill.files[0].sha256 == "abc123"

    def test_round_trip_preserves_multiple_skills(self, tmp_path: Path) -> None:
        state = InstalledState(
            kedro_skills_version="0.1.0",
            skills={
                "skill-a": SkillState(
                    version="0.1.0",
                    files=[FileRecord(path="a.md", sha256="aaa")],
                ),
                "skill-b": SkillState(
                    version="0.2.0",
                    files=[FileRecord(path="b.md", sha256="bbb")],
                ),
            },
        )
        write(tmp_path, state)
        loaded = read(tmp_path)
        assert set(loaded.skills) == {"skill-a", "skill-b"}
        assert loaded.skills["skill-b"].version == "0.2.0"

    def test_written_file_is_valid_json(self, tmp_path: Path) -> None:
        write(tmp_path, _make_state())
        path = tmp_path / ".agents" / "skills" / ".installed.json"
        data = json.loads(path.read_text())
        assert "kedro_skills_version" in data
        assert "skills" in data


class TestRead:
    def test_missing_file_returns_empty(self, tmp_path: Path) -> None:
        state = read(tmp_path)
        assert isinstance(state, InstalledState)
        assert state.skills == {}

    def test_malformed_json_raises(self, tmp_path: Path) -> None:
        path = tmp_path / ".agents" / "skills" / ".installed.json"
        path.parent.mkdir(parents=True)
        path.write_text("{bad json!!")
        with pytest.raises(ValueError, match="Malformed state file"):
            read(tmp_path)

    def test_non_object_raises(self, tmp_path: Path) -> None:
        path = tmp_path / ".agents" / "skills" / ".installed.json"
        path.parent.mkdir(parents=True)
        path.write_text('"just a string"')
        with pytest.raises(ValueError, match="must be a JSON object"):
            read(tmp_path)


class TestAtomicWrite:
    def test_creates_parent_directories(self, tmp_path: Path) -> None:
        write(tmp_path, _make_state())
        assert (tmp_path / ".agents" / "skills" / ".installed.json").is_file()

    def test_no_temp_files_left_behind(self, tmp_path: Path) -> None:
        write(tmp_path, _make_state())
        state_dir = tmp_path / ".agents" / "skills"
        leftover = [f for f in state_dir.iterdir() if f.suffix == ".tmp"]
        assert leftover == []

    def test_overwrite_existing(self, tmp_path: Path) -> None:
        write(tmp_path, _make_state(sha="first"))
        write(tmp_path, _make_state(sha="second"))
        loaded = read(tmp_path)
        assert loaded.skills["catalog-config"].files[0].sha256 == "second"


class TestDetectDrift:
    def _install_file(self, project: Path, rel_path: str, content: str) -> str:
        """Write a file and return its SHA-256."""
        dest = project / rel_path
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(content)
        return hashlib.sha256(content.encode()).hexdigest()

    def test_no_drift_when_unchanged(self, tmp_path: Path) -> None:
        sha = self._install_file(
            tmp_path, ".agents/skills/catalog-config/SKILL.md", "original"
        )
        write(tmp_path, _make_state(sha=sha))

        drifted = detect_drift(tmp_path, "catalog-config")
        assert drifted == []

    def test_drift_when_modified(self, tmp_path: Path) -> None:
        sha = self._install_file(
            tmp_path, ".agents/skills/catalog-config/SKILL.md", "original"
        )
        write(tmp_path, _make_state(sha=sha))

        (tmp_path / ".agents/skills/catalog-config/SKILL.md").write_text("edited!")

        drifted = detect_drift(tmp_path, "catalog-config")
        assert len(drifted) == 1
        assert isinstance(drifted[0], DriftedFile)
        assert drifted[0].expected_sha256 == sha
        assert drifted[0].actual_sha256 is not None
        assert drifted[0].actual_sha256 != sha

    def test_drift_when_file_missing(self, tmp_path: Path) -> None:
        write(tmp_path, _make_state(sha="recorded"))

        drifted = detect_drift(tmp_path, "catalog-config")
        assert len(drifted) == 1
        assert drifted[0].actual_sha256 is None

    def test_unknown_skill_returns_empty(self, tmp_path: Path) -> None:
        write(tmp_path, _make_state())
        assert detect_drift(tmp_path, "nonexistent") == []

    def test_no_state_file_returns_empty(self, tmp_path: Path) -> None:
        assert detect_drift(tmp_path, "catalog-config") == []
