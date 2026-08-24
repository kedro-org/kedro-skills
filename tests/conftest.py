from __future__ import annotations

from typing import TYPE_CHECKING, Any

import pytest

if TYPE_CHECKING:
    from pathlib import Path


@pytest.fixture()
def sent_events(
    monkeypatch: pytest.MonkeyPatch,
) -> list[tuple[str, dict[str, Any]]]:
    """Capture telemetry events instead of dispatching them."""
    from kedro_skills import telemetry  # noqa: PLC0415

    events: list[tuple[str, dict[str, Any]]] = []

    def fake_track_event(
        event_name: str, properties: dict[str, Any], project_root: Path | None
    ) -> None:
        events.append((event_name, properties))

    monkeypatch.setattr(telemetry, "track_event", fake_track_event)
    return events


@pytest.fixture()
def kedro_project(tmp_path: Path) -> Path:
    """Create a minimal directory that Kedro recognises as a project."""
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text(
        "[tool.kedro]\n"
        'package_name = "test_project"\n'
        'project_name = "Test Project"\n'
        'kedro_init_version = "1.4.0"\n'
    )
    (tmp_path / "src" / "test_project").mkdir(parents=True)
    (tmp_path / "src" / "test_project" / "__init__.py").touch()
    return tmp_path


@pytest.fixture()
def non_kedro_dir(tmp_path: Path) -> Path:
    """A plain directory with no Kedro markers."""
    return tmp_path
