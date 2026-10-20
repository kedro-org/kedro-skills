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

Two optional vars change what the model sees:

- ``fixture_overlay``: a directory, relative to ``evals/``, whose files replace
  or add to the snapshot's files for that test (for example
  ``skills/explain-project/overlays/broken-import``). A file named
  ``<name>.deleted`` hides ``<name>`` from the snapshot.
- ``project_tree``: if set to a non-empty value, the context starts with a list
  of every file in the project (snapshot plus overlay), so the model can see
  folders whose files are not shown.
"""

from __future__ import annotations

from pathlib import Path

PROJECT_DIR = Path(__file__).parent / "project"
EVALS_DIR = Path(__file__).parent.parent
DELETED = ".deleted"


def _inside(root: Path, rel: str) -> Path:
    path = (root / rel).resolve()
    if not path.is_relative_to(root.resolve()):
        raise ValueError(f"{rel!r} is outside {root}")
    return path


def _files(root: Path) -> set[str]:
    return {
        p.relative_to(root).as_posix()
        for p in root.rglob("*")
        if p.is_file() and "__pycache__" not in p.parts
    }


def project_tree(overlay: Path | None = None) -> list[str]:
    files = _files(PROJECT_DIR)
    if overlay is not None:
        extra = _files(overlay)
        files |= {f for f in extra if not f.endswith(DELETED)}
        files -= {f[: -len(DELETED)] for f in extra if f.endswith(DELETED)}
    return sorted(files)


def resolve(rel: str, overlay: Path | None = None) -> Path:
    if overlay is not None:
        if _inside(overlay, rel + DELETED).is_file():
            raise FileNotFoundError(f"Fixture file deleted by overlay: {rel}")
        path = _inside(overlay, rel)
        if path.is_file():
            return path
    path = _inside(PROJECT_DIR, rel)
    if not path.is_file():
        raise FileNotFoundError(f"Fixture file not found: {rel}")
    return path


def build_context(paths: list[str], overlay: Path | None = None, tree: bool = False) -> str:
    sections = []
    if tree:
        listing = "\n".join(project_tree(overlay))
        sections.append(f"### Files in the project\n```\n{listing}\n```")
    for rel in paths:
        text = resolve(rel, overlay).read_text().rstrip()
        sections.append(f"### {rel}\n```\n{text}\n```")
    return "\n\n".join(sections)


def get_var(var_name: str, prompt: str, other_vars: dict) -> dict:
    raw = other_vars.get("project_files") or ""
    paths = [p.strip() for p in raw.split(",") if p.strip()]
    try:
        overlay = None
        if other_vars.get("fixture_overlay"):
            overlay = _inside(EVALS_DIR, other_vars["fixture_overlay"].strip())
            if not overlay.is_dir():
                raise FileNotFoundError(f"Overlay not found: {overlay}")
        tree = bool(other_vars.get("project_tree"))
        return {"output": build_context(paths, overlay, tree)}
    except (ValueError, FileNotFoundError) as exc:
        return {"error": str(exc)}
