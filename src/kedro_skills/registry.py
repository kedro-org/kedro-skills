"""Skill registry: loads and validates skill metadata from ``registry.yaml``."""

from __future__ import annotations

import importlib.resources
from dataclasses import dataclass
from pathlib import Path

import yaml


@dataclass(frozen=True)
class SkillMetadata:
    """Metadata for a single skill as declared in ``registry.yaml``."""

    id: str
    category: str
    description: str
    paths: list[str]
    ide_support: list[str]


_REQUIRED_FIELDS = frozenset(SkillMetadata.__dataclass_fields__)


def _validate_entry(entry: object, index: int) -> SkillMetadata:
    """Validate a single registry entry and return a ``SkillMetadata``."""
    if not isinstance(entry, dict):
        raise ValueError(
            f"Registry entry {index} is not a mapping (got {type(entry).__name__})"
        )

    missing = _REQUIRED_FIELDS - entry.keys()
    if missing:
        raise ValueError(
            f"Registry entry {index} ({entry.get('id', '?')}) "
            f"is missing required fields: {', '.join(sorted(missing))}"
        )

    return SkillMetadata(
        id=str(entry["id"]),
        category=str(entry["category"]),
        description=str(entry["description"]).strip(),
        paths=[str(p) for p in entry["paths"]],
        ide_support=[str(i) for i in entry["ide_support"]],
    )


def _resolve_registry_path() -> Path:
    """Locate ``registry.yaml``, supporting both wheel and editable installs."""
    pkg = importlib.resources.files("kedro_skills")
    wheel_path = Path(str(pkg / "registry.yaml"))
    if wheel_path.is_file():
        return wheel_path

    dev_path = Path(str(pkg)).parent.parent / "registry.yaml"
    if dev_path.is_file():
        return dev_path

    raise FileNotFoundError(
        f"Cannot locate registry.yaml. Searched:\n  {wheel_path}\n  {dev_path}"
    )


def load_registry() -> list[SkillMetadata]:
    """Load and validate every skill entry from the packaged ``registry.yaml``.

    Raises ``ValueError`` for malformed entries and ``FileNotFoundError``
    when the registry file is missing from the package.
    """
    raw = _resolve_registry_path().read_text(encoding="utf-8")
    data = yaml.safe_load(raw)

    if not isinstance(data, dict) or "skills" not in data:
        raise ValueError(
            "registry.yaml must be a YAML mapping with a top-level 'skills' key"
        )

    entries = data["skills"]
    if not isinstance(entries, list):
        raise ValueError("'skills' key in registry.yaml must be a list")

    return [_validate_entry(entry, i) for i, entry in enumerate(entries)]


def get_skill(skill_id: str) -> SkillMetadata:
    """Return metadata for *skill_id*, or raise ``KeyError``."""
    skills = load_registry()
    for skill in skills:
        if skill.id == skill_id:
            return skill
    available = [s.id for s in skills]
    raise KeyError(
        f"Unknown skill {skill_id!r}. Available skills: {', '.join(available)}"
    )
