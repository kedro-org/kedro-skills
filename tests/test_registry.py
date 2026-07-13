from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import patch

import pytest
import yaml

from kedro_skills.registry import SkillMetadata, get_skill, load_registry

if TYPE_CHECKING:
    from pathlib import Path


@pytest.fixture()
def _patch_registry(tmp_path: Path):
    """Patch ``importlib.resources.files`` so ``load_registry`` reads from *tmp_path*."""
    yield tmp_path

    def _make_patcher(registry_content: str):
        registry_file = tmp_path / "registry.yaml"
        registry_file.write_text(registry_content)

        return patch(
            "kedro_skills.registry.importlib.resources.files",
            return_value=tmp_path,
        )


def _write_registry(tmp_path: Path, content: str):
    (tmp_path / "registry.yaml").write_text(content)


def _patch_files(tmp_path: Path):
    return patch(
        "kedro_skills.registry.importlib.resources.files",
        return_value=tmp_path,
    )


VALID_REGISTRY = yaml.dump(
    {
        "skills": [
            {
                "id": "catalog-config",
                "category": "data",
                "description": "Catalog guidance",
                "paths": ["conf/**/*.yml"],
                "ide_support": ["cursor", "copilot"],
            }
        ]
    }
)

TWO_SKILLS_REGISTRY = yaml.dump(
    {
        "skills": [
            {
                "id": "catalog-config",
                "category": "data",
                "description": "Catalog guidance",
                "paths": ["conf/**/*.yml"],
                "ide_support": ["cursor"],
            },
            {
                "id": "pipeline-config",
                "category": "pipelines",
                "description": "Pipeline guidance",
                "paths": ["src/**/*.py"],
                "ide_support": ["claude"],
            },
        ]
    }
)


class TestLoadRegistry:
    def test_happy_path(self, tmp_path: Path) -> None:
        _write_registry(tmp_path, VALID_REGISTRY)
        with _patch_files(tmp_path):
            skills = load_registry()

        assert len(skills) == 1
        skill = skills[0]
        assert isinstance(skill, SkillMetadata)
        assert skill.id == "catalog-config"
        assert skill.category == "data"
        assert skill.description == "Catalog guidance"
        assert skill.paths == ["conf/**/*.yml"]
        assert skill.ide_support == ["cursor", "copilot"]

    def test_multiple_skills(self, tmp_path: Path) -> None:
        _write_registry(tmp_path, TWO_SKILLS_REGISTRY)
        with _patch_files(tmp_path):
            skills = load_registry()

        assert len(skills) == 2
        assert skills[0].id == "catalog-config"
        assert skills[1].id == "pipeline-config"

    def test_missing_field_raises(self, tmp_path: Path) -> None:
        bad = yaml.dump(
            {
                "skills": [
                    {
                        "id": "incomplete",
                        "category": "data",
                    }
                ]
            }
        )
        _write_registry(tmp_path, bad)
        with (
            _patch_files(tmp_path),
            pytest.raises(ValueError, match="missing required fields"),
        ):
            load_registry()

    def test_not_a_mapping_raises(self, tmp_path: Path) -> None:
        bad = yaml.dump({"skills": ["just-a-string"]})
        _write_registry(tmp_path, bad)
        with _patch_files(tmp_path), pytest.raises(ValueError, match="not a mapping"):
            load_registry()

    def test_missing_skills_key_raises(self, tmp_path: Path) -> None:
        bad = yaml.dump({"other": []})
        _write_registry(tmp_path, bad)
        with (
            _patch_files(tmp_path),
            pytest.raises(ValueError, match="top-level 'skills' key"),
        ):
            load_registry()

    def test_skills_not_a_list_raises(self, tmp_path: Path) -> None:
        bad = yaml.dump({"skills": "not-a-list"})
        _write_registry(tmp_path, bad)
        with _patch_files(tmp_path), pytest.raises(ValueError, match="must be a list"):
            load_registry()

    def test_invalid_yaml_type_raises(self, tmp_path: Path) -> None:
        _write_registry(tmp_path, "just a plain string")
        with (
            _patch_files(tmp_path),
            pytest.raises(ValueError, match="top-level 'skills' key"),
        ):
            load_registry()


class TestGetSkill:
    def test_known_skill(self, tmp_path: Path) -> None:
        _write_registry(tmp_path, VALID_REGISTRY)
        with _patch_files(tmp_path):
            skill = get_skill("catalog-config")

        assert skill.id == "catalog-config"

    def test_unknown_skill_raises(self, tmp_path: Path) -> None:
        _write_registry(tmp_path, VALID_REGISTRY)
        with (
            _patch_files(tmp_path),
            pytest.raises(KeyError, match="Unknown skill 'nonexistent'"),
        ):
            get_skill("nonexistent")

    def test_unknown_skill_lists_available(self, tmp_path: Path) -> None:
        _write_registry(tmp_path, TWO_SKILLS_REGISTRY)
        with (
            _patch_files(tmp_path),
            pytest.raises(KeyError, match="catalog-config, pipeline-config"),
        ):
            get_skill("missing")
