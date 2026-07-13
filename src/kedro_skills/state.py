from __future__ import annotations

import contextlib
import json
import os
import tempfile
from dataclasses import asdict, dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

    from kedro_skills.installer import FileRecord

from kedro_skills import __version__
from kedro_skills.installer import compute_sha256

STATE_FILENAME = ".agents/skills/.installed.json"


@dataclass
class SkillState:
    """Recorded state of a single installed skill."""

    version: str
    files: list[FileRecord]


@dataclass
class InstalledState:
    """Top-level state persisted in ``.installed.json``."""

    kedro_skills_version: str = field(default_factory=lambda: __version__)
    skills: dict[str, SkillState] = field(default_factory=dict)


@dataclass(frozen=True)
class DriftedFile:
    """Describes a managed file whose on-disk content diverges from the
    recorded checksum (or is missing entirely)."""

    path: str
    expected_sha256: str
    actual_sha256: str | None


def _state_path(project_root: Path) -> Path:
    return project_root / STATE_FILENAME


def read(project_root: Path) -> InstalledState:
    """Load ``.installed.json`` and return an :class:`InstalledState`.

    Returns a fresh, empty state when the file does not exist.
    Raises ``ValueError`` for malformed JSON.
    """
    path = _state_path(project_root)
    if not path.is_file():
        return InstalledState()

    text = path.read_text(encoding="utf-8")
    try:
        raw = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Malformed state file {path}: {exc}") from exc

    if not isinstance(raw, dict):
        raise ValueError(f"State file {path} must be a JSON object")

    from kedro_skills.installer import FileRecord  # noqa: PLC0415

    skills: dict[str, SkillState] = {}
    for skill_id, skill_data in raw.get("skills", {}).items():
        files = [
            FileRecord(path=f["path"], sha256=f["sha256"])
            for f in skill_data.get("files", [])
        ]
        skills[skill_id] = SkillState(
            version=skill_data.get("version", ""),
            files=files,
        )

    return InstalledState(
        kedro_skills_version=raw.get("kedro_skills_version", __version__),
        skills=skills,
    )


def write(project_root: Path, state: InstalledState) -> None:
    """Atomically persist *state* to ``.installed.json``.

    Uses a temporary file + ``os.replace`` so readers never see a
    partially-written file.
    """
    path = _state_path(project_root)
    path.parent.mkdir(parents=True, exist_ok=True)

    data = asdict(state)
    payload = json.dumps(data, indent=2, sort_keys=True) + "\n"

    fd, tmp = tempfile.mkstemp(
        dir=str(path.parent), prefix=".installed_", suffix=".tmp"
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(payload)
        os.replace(tmp, str(path))
    except BaseException:
        with contextlib.suppress(OSError):
            os.unlink(tmp)
        raise


def detect_drift(project_root: Path, skill_id: str) -> list[DriftedFile]:
    """Compare on-disk checksums against the recorded state for *skill_id*.

    Returns an empty list when nothing has drifted.  Each
    :class:`DriftedFile` entry describes a file that was modified or
    deleted since it was installed.
    """
    installed = read(project_root)

    if skill_id not in installed.skills:
        return []

    drifted: list[DriftedFile] = []
    for rec in installed.skills[skill_id].files:
        abs_path = project_root / rec.path
        if not abs_path.is_file():
            drifted.append(
                DriftedFile(
                    path=rec.path,
                    expected_sha256=rec.sha256,
                    actual_sha256=None,
                )
            )
        else:
            actual = compute_sha256(abs_path)
            if actual != rec.sha256:
                drifted.append(
                    DriftedFile(
                        path=rec.path,
                        expected_sha256=rec.sha256,
                        actual_sha256=actual,
                    )
                )

    return drifted
