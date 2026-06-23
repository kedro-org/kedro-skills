from __future__ import annotations

from pathlib import Path

import click


def find_project_root() -> Path:
    """Return the Kedro project root for the current working directory.

    Wraps ``kedro.utils.find_kedro_project`` and raises a friendly
    ``click.UsageError`` when invoked outside a Kedro project.
    """
    from kedro.utils import find_kedro_project

    project_path = find_kedro_project(Path.cwd())
    if project_path is None:
        raise click.UsageError(
            "Not inside a Kedro project. "
            "Please change to a Kedro project directory and try again."
        )
    return project_path
