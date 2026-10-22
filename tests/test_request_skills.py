"""Request-based skills install without file-scoped activation or project files."""

from __future__ import annotations

from dataclasses import replace
from typing import TYPE_CHECKING
from unittest.mock import patch

import pytest
import yaml

from kedro_skills.orchestrator import install_skill, uninstall_skill, update_skills
from kedro_skills.registry import get_skill

if TYPE_CHECKING:
    from pathlib import Path


def _frontmatter(path: Path) -> dict:
    return yaml.safe_load(path.read_text().split("---", 2)[1])


@pytest.mark.parametrize("has_project", [False, True])
def test_install_request_skill(tmp_path: Path, has_project: bool) -> None:
    pyproject = tmp_path / "pyproject.toml"
    original = b"# Existing project configuration must stay untouched.\n"
    if has_project:
        pyproject.write_bytes(original)

    assert get_skill("kedro-build-demo").paths == []
    result = install_skill("kedro-build-demo", tmp_path)
    assert not result.refused

    cursor = _frontmatter(tmp_path / ".cursor/rules/kedro-build-demo.mdc")
    copilot = _frontmatter(
        tmp_path / ".github/instructions/kedro-build-demo.instructions.md"
    )
    assert cursor["description"] == copilot["description"]
    assert cursor["description"] == get_skill("kedro-build-demo").description
    assert "globs" not in cursor
    assert cursor["alwaysApply"] is False
    assert "applyTo" not in copilot

    for relative in (
        "AGENTS.md",
        ".cursor/rules/kedro-build-demo.mdc",
        ".github/instructions/kedro-build-demo.instructions.md",
    ):
        content = (tmp_path / relative).read_text()
        assert "user's request matches" in content
        assert ".agents/skills/kedro-build-demo/SKILL.md" in content
        assert "files matching" not in content
        assert "pyproject.toml" not in content

    canonical = tmp_path / ".agents/skills/kedro-build-demo/SKILL.md"
    claude = tmp_path / ".claude/skills/kedro-build-demo/SKILL.md"
    assert claude.read_bytes() == canonical.read_bytes()
    if has_project:
        assert pyproject.read_bytes() == original
    else:
        assert not pyproject.exists()


def test_update_replaces_file_activation(tmp_path: Path) -> None:
    user_rules = "# User rules\n\nPreserve this guidance.\n"
    (tmp_path / "AGENTS.md").write_text(user_rules)
    legacy = replace(get_skill("kedro-build-demo"), paths=["pyproject.toml"])
    with patch("kedro_skills.orchestrator.get_skill", return_value=legacy):
        install_skill("kedro-build-demo", tmp_path)

    assert _frontmatter(tmp_path / ".cursor/rules/kedro-build-demo.mdc")["globs"]
    results = update_skills(tmp_path)
    assert len(results) == 1
    assert not results[0].refused
    assert "globs" not in _frontmatter(tmp_path / ".cursor/rules/kedro-build-demo.mdc")
    assert "applyTo" not in _frontmatter(
        tmp_path / ".github/instructions/kedro-build-demo.instructions.md"
    )
    agents = (tmp_path / "AGENTS.md").read_text()
    assert agents.startswith(user_rules)
    assert agents.count("<!-- kedro-skills:kedro-build-demo:start -->") == 1
    assert "pyproject.toml" not in agents

    result = uninstall_skill("kedro-build-demo", tmp_path)
    assert not result.refused
    assert (tmp_path / "AGENTS.md").read_text().strip() == user_rules.strip()
    assert not (tmp_path / ".cursor/rules/kedro-build-demo.mdc").exists()
    assert not (
        tmp_path / ".github/instructions/kedro-build-demo.instructions.md"
    ).exists()
