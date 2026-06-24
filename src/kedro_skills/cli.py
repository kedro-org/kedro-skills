from __future__ import annotations

import click

from kedro_skills.utils import find_project_root


@click.group(name="kedro-skills")
def commands() -> None:
    pass


@commands.group(name="skills")
def skills() -> None:
    """Distribute AI coding skills to Kedro projects."""


@skills.command(name="list")
def list_skills() -> None:
    """List installed skills in the current Kedro project."""
    find_project_root()
    click.echo("No skills installed.")
