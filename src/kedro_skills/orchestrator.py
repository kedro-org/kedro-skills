"""Orchestrator: high-level install/update/uninstall logic."""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from kedro_skills import __version__
from kedro_skills.installer import FileRecord, write_canonical
from kedro_skills.registry import get_skill
from kedro_skills.renderers import agents_md, claude, copilot, cursor
from kedro_skills.state import DriftedFile, SkillState

if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path

    from kedro_skills.registry import SkillMetadata

    _RendererFn = Callable[[SkillMetadata, Path], list[FileRecord]]

_IDE_RENDERERS: dict[str, _RendererFn] = {
    "cursor": cursor.render,
    "copilot": copilot.render,
    "claude": claude.render,
}

_VALID_IDES = frozenset(_IDE_RENDERERS.keys())

_BLOCK_START_RE = re.compile(r"<!-- kedro-skills:(.+?):start -->")
_BLOCK_END_TEMPLATE = "<!-- kedro-skills:{block_id}:end -->"


@dataclass
class OperationResult:
    """Outcome of an install/update/uninstall operation."""

    skill_id: str
    operation: str  # "install" | "update" | "uninstall"
    requested_ides: list[str]
    written: list[FileRecord] = field(default_factory=list)
    refused: list[DriftedFile] = field(default_factory=list)


def _extract_block(content: str, block_id: str) -> str | None:
    """Extract the managed block (markers inclusive) for *block_id* from *content*."""
    start_marker = f"<!-- {block_id}:start -->"
    end_marker = f"<!-- {block_id}:end -->"
    pattern = re.compile(
        re.escape(start_marker) + r".*?" + re.escape(end_marker),
        re.DOTALL,
    )
    match = pattern.search(content)
    if match:
        return match.group(0)
    return None


def check_drift_for_skill(project_root: Path, skill_id: str) -> list[DriftedFile]:
    """Block-aware drift check that handles AGENTS.md blocks correctly.

    For ``agents_md_block`` records, extracts the block between markers,
    hashes only that text, and compares against the stored SHA-256.
    For other record kinds, delegates to normal full-file drift detection.
    """
    from kedro_skills.state import read  # noqa: PLC0415

    installed = read(project_root)
    if skill_id not in installed.skills:
        return []

    drifted: list[DriftedFile] = []
    for rec in installed.skills[skill_id].files:
        abs_path = project_root / rec.path
        if rec.kind == "agents_md_block" and rec.block_id:
            if not abs_path.is_file():
                drifted.append(
                    DriftedFile(
                        path=rec.path,
                        expected_sha256=rec.sha256,
                        actual_sha256=None,
                    )
                )
                continue
            content = abs_path.read_text(encoding="utf-8")
            block_text = _extract_block(content, rec.block_id)
            if block_text is None:
                drifted.append(
                    DriftedFile(
                        path=rec.path,
                        expected_sha256=rec.sha256,
                        actual_sha256=None,
                    )
                )
            else:
                actual = hashlib.sha256(block_text.encode("utf-8")).hexdigest()
                if actual != rec.sha256:
                    drifted.append(
                        DriftedFile(
                            path=rec.path,
                            expected_sha256=rec.sha256,
                            actual_sha256=actual,
                        )
                    )
        elif not abs_path.is_file():
            drifted.append(
                DriftedFile(
                    path=rec.path,
                    expected_sha256=rec.sha256,
                    actual_sha256=None,
                )
            )
        else:
            from kedro_skills.installer import compute_sha256  # noqa: PLC0415

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


def _dispatch_renderers(
    skill: SkillMetadata, project_root: Path, ides: list[str] | None
) -> list[FileRecord]:
    """Run agents_md unconditionally, then IDE-specific renderers."""
    records: list[FileRecord] = []
    records.extend(agents_md.render(skill, project_root))

    target_ides = (
        [ide for ide in skill.ide_support if ide in _VALID_IDES]
        if ides is None
        else [ide for ide in ides if ide in _VALID_IDES]
    )

    for ide in target_ides:
        renderer = _IDE_RENDERERS[ide]
        records.extend(renderer(skill, project_root))

    return records


def install_skill(
    skill_id: str,
    project_root: Path,
    ides: list[str] | None = None,
    force: bool = False,
) -> OperationResult:
    """Install a single skill into the project."""
    skill = get_skill(skill_id)
    requested = (
        ides if ides is not None else [i for i in skill.ide_support if i in _VALID_IDES]
    )

    drifted = check_drift_for_skill(project_root, skill_id)
    if drifted and not force:
        return OperationResult(
            skill_id=skill_id,
            operation="install",
            requested_ides=requested,
            refused=drifted,
        )

    canonical_record = write_canonical(skill, project_root)
    all_records: list[FileRecord] = [canonical_record]
    all_records.extend(_dispatch_renderers(skill, project_root, ides))

    from kedro_skills import state  # noqa: PLC0415

    installed = state.read(project_root)
    installed.skills[skill_id] = SkillState(version=__version__, files=all_records)
    state.write(project_root, installed)

    return OperationResult(
        skill_id=skill_id,
        operation="install",
        requested_ides=requested,
        written=all_records,
    )


def update_skills(project_root: Path, force: bool = False) -> list[OperationResult]:
    """Re-install all currently installed skills."""
    from kedro_skills import state  # noqa: PLC0415

    installed = state.read(project_root)
    if not installed.skills:
        return []

    results: list[OperationResult] = []
    for skill_id in list(installed.skills.keys()):
        drifted = check_drift_for_skill(project_root, skill_id)
        if drifted and not force:
            skill = get_skill(skill_id)
            requested = [i for i in skill.ide_support if i in _VALID_IDES]
            results.append(
                OperationResult(
                    skill_id=skill_id,
                    operation="update",
                    requested_ides=requested,
                    refused=drifted,
                )
            )
        else:
            result = install_skill(skill_id, project_root, force=True)
            results.append(
                OperationResult(
                    skill_id=result.skill_id,
                    operation="update",
                    requested_ides=result.requested_ides,
                    written=result.written,
                    refused=result.refused,
                )
            )

    return results


def uninstall_skill(
    skill_id: str, project_root: Path, force: bool = False
) -> OperationResult:
    """Remove all managed files for *skill_id* from the project."""
    from kedro_skills import state  # noqa: PLC0415

    installed = state.read(project_root)
    if skill_id not in installed.skills:
        raise KeyError(
            f"Skill {skill_id!r} is not installed. "
            f"Installed skills: {', '.join(installed.skills.keys()) or 'none'}"
        )

    skill_state = installed.skills[skill_id]
    skill = get_skill(skill_id)
    requested = [i for i in skill.ide_support if i in _VALID_IDES]

    written: list[FileRecord] = []
    refused: list[DriftedFile] = []

    drifted_set: set[str] = set()
    if not force:
        for d in check_drift_for_skill(project_root, skill_id):
            drifted_set.add(d.path)
            refused.append(d)

    for rec in skill_state.files:
        if rec.path in drifted_set:
            continue

        abs_path = project_root / rec.path

        if rec.kind == "agents_md_block" and rec.block_id:
            _remove_agents_md_block(abs_path, rec.block_id)
        else:
            if abs_path.is_file():
                abs_path.unlink()
            _cleanup_empty_parents(abs_path.parent, project_root)

        written.append(rec)

    del installed.skills[skill_id]

    if installed.skills:
        state.write(project_root, installed)
    else:
        state_path = project_root / state.STATE_FILENAME
        if state_path.is_file():
            state_path.unlink()

    return OperationResult(
        skill_id=skill_id,
        operation="uninstall",
        requested_ides=requested,
        written=written,
        refused=refused,
    )


_WELL_KNOWN_ROOTS = frozenset([".cursor", ".github", ".claude", ".agents"])


def _cleanup_empty_parents(directory: Path, project_root: Path) -> None:
    """Remove empty parent directories up to (but not including) well-known roots."""
    current = directory
    while current != project_root:
        if current.name in _WELL_KNOWN_ROOTS:
            break
        try:
            current.rmdir()
        except OSError:
            break
        current = current.parent


def _remove_agents_md_block(agents_md_path: Path, block_id: str) -> None:
    """Remove the managed block from AGENTS.md; delete the file if it becomes empty."""
    if not agents_md_path.is_file():
        return

    content = agents_md_path.read_text(encoding="utf-8")
    start_marker = f"<!-- {block_id}:start -->"
    end_marker = f"<!-- {block_id}:end -->"
    pattern = re.compile(
        r"\n?" + re.escape(start_marker) + r".*?" + re.escape(end_marker) + r"\n?",
        re.DOTALL,
    )
    new_content = pattern.sub("", content)

    stripped = new_content.strip()
    if not stripped or _is_header_only(stripped):
        agents_md_path.unlink()
        _cleanup_empty_parents(agents_md_path.parent, agents_md_path.parent)
    else:
        agents_md_path.write_text(new_content, encoding="utf-8")


def _is_header_only(text: str) -> bool:
    """Return True if text is just the AGENTS.md header with no skill blocks."""
    from kedro_skills.renderers.agents_md import _HEADER  # noqa: PLC0415

    header_lines = {line.strip() for line in _HEADER.splitlines() if line.strip()}
    content_lines = [line.strip() for line in text.splitlines() if line.strip()]
    return all(line in header_lines for line in content_lines)
