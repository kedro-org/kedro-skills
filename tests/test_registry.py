from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import patch

import pytest
import yaml

from kedro_skills.registry import (
    SkillMetadata,
    get_skill,
    load_registry,
    validate_skill_id,
)

if TYPE_CHECKING:
    from pathlib import Path


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
                "id": "kedro-catalog-config",
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
                "id": "kedro-catalog-config",
                "category": "data",
                "description": "Catalog guidance",
                "paths": ["conf/**/*.yml"],
                "ide_support": ["cursor"],
            },
            {
                "id": "kedro-pipeline-config",
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
        assert skill.id == "kedro-catalog-config"
        assert skill.category == "data"
        assert skill.description == "Catalog guidance"
        assert skill.paths == ["conf/**/*.yml"]
        assert skill.ide_support == ["cursor", "copilot"]

    def test_multiple_skills(self, tmp_path: Path) -> None:
        _write_registry(tmp_path, TWO_SKILLS_REGISTRY)
        with _patch_files(tmp_path):
            skills = load_registry()

        assert len(skills) == 2
        assert skills[0].id == "kedro-catalog-config"
        assert skills[1].id == "kedro-pipeline-config"

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

    def test_id_without_prefix_raises(self, tmp_path: Path) -> None:
        bad = VALID_REGISTRY.replace("kedro-catalog-config", "catalog-config")
        _write_registry(tmp_path, bad)
        with (
            _patch_files(tmp_path),
            pytest.raises(
                ValueError, match="'catalog-config' must start with 'kedro-'"
            ),
        ):
            load_registry()


class TestValidateSkillId:
    @pytest.mark.parametrize(
        "skill_id",
        ["kedro-catalog-config", "kedro-x", "kedro-v2-api", "kedro-" + "a" * 58],
    )
    def test_valid_id(self, skill_id: str) -> None:
        validate_skill_id(skill_id)

    @pytest.mark.parametrize(
        "skill_id", ["catalog-config", "kedro", "kedrocatalog", "Kedro-catalog", ""]
    )
    def test_id_without_prefix_raises(self, skill_id: str) -> None:
        with pytest.raises(ValueError, match="must start with 'kedro-'"):
            validate_skill_id(skill_id)

    def test_id_without_prefix_suggests_prefixed_id(self) -> None:
        with pytest.raises(ValueError, match="for example 'kedro-build-demo'"):
            validate_skill_id("build-demo")

    @pytest.mark.parametrize(
        "skill_id",
        [
            "kedro-",
            "kedro-Catalog",
            "kedro-catalog_config",
            "kedro-catalog config",
            "kedro--catalog",
            "kedro-catalog-",
            "kedro-" + "a" * 59,
        ],
    )
    def test_malformed_id_raises(self, skill_id: str) -> None:
        with pytest.raises(
            ValueError, match="lowercase letters, digits and single hyphens"
        ):
            validate_skill_id(skill_id)


class TestGetSkill:
    def test_known_skill(self, tmp_path: Path) -> None:
        _write_registry(tmp_path, VALID_REGISTRY)
        with _patch_files(tmp_path):
            skill = get_skill("kedro-catalog-config")

        assert skill.id == "kedro-catalog-config"

    def test_unknown_skill_raises(self, tmp_path: Path) -> None:
        _write_registry(tmp_path, VALID_REGISTRY)
        with (
            _patch_files(tmp_path),
            pytest.raises(KeyError, match="Unknown skill 'nonexistent'"),
        ):
            get_skill("nonexistent")

    def test_renamed_skill_names_new_id(self, tmp_path: Path) -> None:
        _write_registry(tmp_path, VALID_REGISTRY)
        with (
            _patch_files(tmp_path),
            pytest.raises(KeyError, match="renamed to 'kedro-catalog-config'"),
        ):
            get_skill("catalog-config")

    def test_unknown_skill_lists_available(self, tmp_path: Path) -> None:
        _write_registry(tmp_path, TWO_SKILLS_REGISTRY)
        with (
            _patch_files(tmp_path),
            pytest.raises(
                KeyError, match="kedro-catalog-config, kedro-pipeline-config"
            ),
        ):
            get_skill("missing")
