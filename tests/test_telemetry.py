from __future__ import annotations

import sys
import types
from typing import TYPE_CHECKING, Any

from kedro_skills import telemetry
from kedro_skills.installer import FileRecord
from kedro_skills.orchestrator import OperationResult
from kedro_skills.state import DriftedFile

if TYPE_CHECKING:
    from pathlib import Path

    import pytest

_RECORD = FileRecord(path=".agents/skills/x/SKILL.md", sha256="abc")
_DRIFT = DriftedFile(
    path=".agents/skills/x/SKILL.md", expected_sha256="abc", actual_sha256="def"
)


def _result(
    operation: str,
    written: bool = True,
    refused: bool = False,
    skill_id: str = "catalog-config",
) -> OperationResult:
    return OperationResult(
        skill_id=skill_id,
        operation=operation,
        requested_ides=["cursor", "claude"],
        written=[_RECORD] if written else [],
        refused=[_DRIFT] if refused else [],
    )


class TestSafeSkillId:
    def test_registry_skill_id_passes_through(self) -> None:
        assert telemetry.safe_skill_id("catalog-config") == "catalog-config"

    def test_unknown_id_is_masked(self) -> None:
        assert telemetry.safe_skill_id("../../etc/passwd") == "unknown"

    def test_none_is_masked(self) -> None:
        assert telemetry.safe_skill_id(None) == "unknown"


class TestTrackEvent:
    def test_sends_through_kedro_telemetry_api(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        calls: list[tuple[Any, ...]] = []

        fake_api = types.ModuleType("kedro_telemetry.api")
        fake_api.send_telemetry_event = (  # type: ignore[attr-defined]
            lambda event_name, properties, project_path: calls.append(
                (event_name, properties, project_path)
            )
        )
        fake_pkg = types.ModuleType("kedro_telemetry")
        fake_pkg.api = fake_api  # type: ignore[attr-defined]
        monkeypatch.setitem(sys.modules, "kedro_telemetry", fake_pkg)
        monkeypatch.setitem(sys.modules, "kedro_telemetry.api", fake_api)

        telemetry.track_event("kedro_skills_install", {"skill_id": "x"}, tmp_path)

        assert calls == [("kedro_skills_install", {"skill_id": "x"}, tmp_path)]

    def test_noop_when_kedro_telemetry_missing(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setitem(sys.modules, "kedro_telemetry", None)
        monkeypatch.setitem(sys.modules, "kedro_telemetry.api", None)

        telemetry.track_event("kedro_skills_install", {"skill_id": "x"}, None)

    def test_api_errors_are_suppressed(self, monkeypatch: pytest.MonkeyPatch) -> None:
        def boom(
            event_name: str, properties: dict[str, Any], project_path: Any
        ) -> None:
            raise RuntimeError("network down")

        fake_api = types.ModuleType("kedro_telemetry.api")
        fake_api.send_telemetry_event = boom  # type: ignore[attr-defined]
        fake_pkg = types.ModuleType("kedro_telemetry")
        fake_pkg.api = fake_api  # type: ignore[attr-defined]
        monkeypatch.setitem(sys.modules, "kedro_telemetry", fake_pkg)
        monkeypatch.setitem(sys.modules, "kedro_telemetry.api", fake_api)

        telemetry.track_event("kedro_skills_install", {"skill_id": "x"}, None)


class TestTrackInstall:
    def test_successful_install(
        self, sent_events: list[tuple[str, dict[str, Any]]], tmp_path: Path
    ) -> None:
        telemetry.track_install(
            _result("install"), install_all=False, project_root=tmp_path
        )

        assert sent_events == [
            (
                "kedro_skills_install",
                {
                    "skill_id": "catalog-config",
                    "target_ides": "claude,cursor",
                    "install_all": False,
                    "success": True,
                },
            )
        ]

    def test_refused_install_reports_failure(
        self, sent_events: list[tuple[str, dict[str, Any]]], tmp_path: Path
    ) -> None:
        telemetry.track_install(
            _result("install", written=False, refused=True),
            install_all=True,
            project_root=tmp_path,
        )

        _, properties = sent_events[0]
        assert properties["success"] is False
        assert properties["install_all"] is True

    def test_install_failure_masks_unknown_id(
        self, sent_events: list[tuple[str, dict[str, Any]]], tmp_path: Path
    ) -> None:
        telemetry.track_install_failure(
            "no-such-skill", install_all=False, project_root=tmp_path
        )

        assert sent_events == [
            (
                "kedro_skills_install",
                {"skill_id": "unknown", "install_all": False, "success": False},
            )
        ]


class TestTrackUpdate:
    def test_mixed_results(
        self, sent_events: list[tuple[str, dict[str, Any]]], tmp_path: Path
    ) -> None:
        results = [
            _result("update"),
            _result("update", written=False, refused=True, skill_id="other"),
        ]

        telemetry.track_update(results, tmp_path)

        assert sent_events == [
            (
                "kedro_skills_update",
                {"skills_updated": 1, "drift_detected": True, "success": True},
            )
        ]

    def test_nothing_installed(
        self, sent_events: list[tuple[str, dict[str, Any]]], tmp_path: Path
    ) -> None:
        telemetry.track_update([], tmp_path)

        assert sent_events == [
            (
                "kedro_skills_update",
                {"skills_updated": 0, "drift_detected": False, "success": True},
            )
        ]

    def test_failure(
        self, sent_events: list[tuple[str, dict[str, Any]]], tmp_path: Path
    ) -> None:
        telemetry.track_update_failure(tmp_path)

        assert sent_events == [("kedro_skills_update", {"success": False})]


class TestTrackUninstall:
    def test_uninstall(
        self, sent_events: list[tuple[str, dict[str, Any]]], tmp_path: Path
    ) -> None:
        telemetry.track_uninstall(_result("uninstall"), tmp_path)

        assert sent_events == [
            ("kedro_skills_uninstall", {"skill_id": "catalog-config"})
        ]
