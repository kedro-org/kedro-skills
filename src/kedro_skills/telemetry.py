"""Optional usage-analytics bridge to `kedro-telemetry`.

Events are sent through `kedro_telemetry.api.send_telemetry_event`, which
applies the standard Kedro telemetry consent flow (`DO_NOT_TRACK`,
`KEDRO_DISABLE_TELEMETRY`, the project's `.telemetry` file). When
`kedro-telemetry` is not installed, or does not yet expose the API, every
function in this module is a silent no-op — telemetry must never break or
slow down the CLI beyond a single best-effort dispatch.

Only data shipped with this package (skill ids, IDE names) and operation
outcomes are reported; never file paths, skill content or project details.
"""

from __future__ import annotations

import contextlib
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from pathlib import Path

    from kedro_skills.orchestrator import OperationResult

EVENT_INSTALL = "kedro_skills_install"
EVENT_UPDATE = "kedro_skills_update"
EVENT_UNINSTALL = "kedro_skills_uninstall"

UNKNOWN_SKILL_ID = "unknown"


def safe_skill_id(skill_id: str | None) -> str:
    """Return `skill_id` if it names a skill in the registry, else `unknown`.

    Telemetry must only ever report identifiers shipped with the package;
    arbitrary user input could contain anything, so it is never echoed.
    """
    from kedro_skills.registry import load_registry  # noqa: PLC0415

    try:
        registry_ids = {skill.id for skill in load_registry()}
    except Exception:
        return UNKNOWN_SKILL_ID
    if skill_id and skill_id in registry_ids:
        return skill_id
    return UNKNOWN_SKILL_ID


def track_event(
    event_name: str, properties: dict[str, Any], project_root: Path | None
) -> None:
    """Fire-and-forget a usage event through `kedro-telemetry`, if present."""
    try:
        from kedro_telemetry.api import send_telemetry_event  # noqa: PLC0415
    except ImportError:
        return
    with contextlib.suppress(Exception):
        send_telemetry_event(event_name, properties, project_path=project_root)


def track_install(
    result: OperationResult, install_all: bool, project_root: Path
) -> None:
    """Report one completed (or drift-refused) install of a single skill."""
    track_event(
        EVENT_INSTALL,
        {
            "skill_id": result.skill_id,
            "target_ides": ",".join(sorted(result.requested_ides)),
            "install_all": install_all,
            "success": bool(result.written),
        },
        project_root,
    )


def track_install_failure(
    skill_id: str | None, install_all: bool, project_root: Path
) -> None:
    """Report an install that errored before any files were written."""
    track_event(
        EVENT_INSTALL,
        {
            "skill_id": safe_skill_id(skill_id),
            "install_all": install_all,
            "success": False,
        },
        project_root,
    )


def track_update(results: list[OperationResult], project_root: Path) -> None:
    """Report one `kedro skills update` run, summarised across all skills."""
    track_event(
        EVENT_UPDATE,
        {
            "skills_updated": sum(1 for result in results if result.written),
            "drift_detected": any(result.refused for result in results),
            "success": True,
        },
        project_root,
    )


def track_update_failure(project_root: Path) -> None:
    """Report an update run that errored before completing."""
    track_event(EVENT_UPDATE, {"success": False}, project_root)


def track_uninstall(result: OperationResult, project_root: Path) -> None:
    """Report one completed uninstall of a single skill."""
    track_event(EVENT_UNINSTALL, {"skill_id": result.skill_id}, project_root)
