"""IDE-specific renderers for Kedro skills.

Each renderer is a pure function with the signature::

    render(skill: SkillMetadata, project_root: Path) -> list[FileRecord]

Renderers write (or update) IDE-specific files and return ``FileRecord``
entries for the orchestrator to merge into ``.installed.json``.  They never
read ``.installed.json`` themselves.
"""

from kedro_skills.renderers.agents_md import render as render_agents_md
from kedro_skills.renderers.claude import render as render_claude
from kedro_skills.renderers.copilot import render as render_copilot
from kedro_skills.renderers.cursor import render as render_cursor

__all__ = ["render_agents_md", "render_claude", "render_copilot", "render_cursor"]
