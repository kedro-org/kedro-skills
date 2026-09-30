"""promptfoo variable loader that builds project context from the fixture snapshot.

Use it in a promptfooconfig.yaml as a var whose value is this file. The test's
``project_files`` var is a comma-separated list of paths relative to
``evals/fixture/project/``. It is a string, not a YAML list, because promptfoo
expands list-valued vars into one test case per element:

    defaultTest:
      vars:
        project_context: file://../../fixture/context.py
    tests:
      - vars:
          project_files: conf/base/catalog.yml, conf/base/parameters.yml
"""

from __future__ import annotations

from pathlib import Path

PROJECT_DIR = Path(__file__).parent / "project"


def build_context(paths: list[str]) -> str:
    sections = []
    for rel in paths:
        path = (PROJECT_DIR / rel).resolve()
        if not path.is_relative_to(PROJECT_DIR.resolve()):
            raise ValueError(f"{rel!r} is outside the fixture project")
        if not path.is_file():
            raise FileNotFoundError(f"Fixture file not found: {rel}")
        sections.append(f"### {rel}\n```\n{path.read_text().rstrip()}\n```")
    return "\n\n".join(sections)


def get_var(var_name: str, prompt: str, other_vars: dict) -> dict:
    raw = other_vars.get("project_files") or ""
    paths = [p.strip() for p in raw.split(",") if p.strip()]
    try:
        return {"output": build_context(paths)}
    except (ValueError, FileNotFoundError) as exc:
        return {"error": str(exc)}
