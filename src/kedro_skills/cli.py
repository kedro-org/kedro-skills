from __future__ import annotations

import click


@click.group(name="kedro-skills")
def commands() -> None:
    pass


@commands.group(name="skills")
def skills() -> None:
    """Distribute AI coding skills to Kedro projects."""
