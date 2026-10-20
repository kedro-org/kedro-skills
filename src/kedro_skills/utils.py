from __future__ import annotations

from pathlib import Path

import click


def find_project_root() -> Path:
    """Return the directory skills should be installed into.

    This is the Kedro project root, or the current directory if there
    isn't one.
    """
    from kedro.utils import find_kedro_project  # noqa: PLC0415

    cwd = Path.cwd()
    project_path: Path | None = find_kedro_project(cwd)
    if project_path is None:
        click.echo(
            f"Not inside a Kedro project; using the current directory ({cwd}).",
            err=True,
        )
        return cwd
    return project_path
