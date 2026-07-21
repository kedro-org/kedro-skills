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
    """List available skills and their install status."""
    project_root = find_project_root()

    from kedro_skills.registry import load_registry  # noqa: PLC0415
    from kedro_skills.state import read  # noqa: PLC0415

    registry = load_registry()
    installed = read(project_root)

    click.echo("\nAvailable skills:\n")
    click.echo(f"  {'ID':<20} {'Category':<12} {'Status':<14} Description")
    click.echo(f"  {'─' * 20} {'─' * 12} {'─' * 14} {'─' * 40}")

    for skill in registry:
        if skill.id in installed.skills:
            version = installed.skills[skill.id].version
            status = f"v{version} ✓"
        else:
            status = "not installed"
        _max_desc = 50
        desc = (
            skill.description[:_max_desc] + "..."
            if len(skill.description) > _max_desc
            else skill.description
        )
        click.echo(f"  {skill.id:<20} {skill.category:<12} {status:<14} {desc}")

    click.echo()


def _parse_ides(ides_str: str | None) -> list[str] | None:
    """Parse and validate the --ide comma-separated string."""
    if ides_str is None:
        return None
    valid = {"cursor", "copilot", "claude"}
    ides = [i.strip() for i in ides_str.split(",") if i.strip()]
    invalid = set(ides) - valid
    if invalid:
        raise click.BadParameter(
            f"Unknown IDE(s): {', '.join(sorted(invalid))}. "
            f"Valid options: {', '.join(sorted(valid))}"
        )
    return ides


@skills.command(name="install")
@click.argument("skill_id", required=False)
@click.option(
    "--all", "install_all", is_flag=True, help="Install all available skills."
)
@click.option(
    "--ide",
    "ides",
    default=None,
    help="Comma-separated list of IDEs (cursor,copilot,claude).",
)
@click.option(
    "--force", is_flag=True, help="Overwrite files even if they have been modified."
)
def install_cmd(
    skill_id: str | None,
    install_all: bool,
    ides: str | None,
    force: bool,
) -> None:
    """Install a skill into the current Kedro project."""
    project_root = find_project_root()
    parsed_ides = _parse_ides(ides)

    from kedro_skills.orchestrator import install_skill  # noqa: PLC0415
    from kedro_skills.registry import load_registry  # noqa: PLC0415

    if install_all:
        registry = load_registry()
        for skill in registry:
            result = install_skill(
                skill.id, project_root, ides=parsed_ides, force=force
            )
            _print_result(result)
    elif skill_id:
        try:
            result = install_skill(
                skill_id, project_root, ides=parsed_ides, force=force
            )
        except KeyError as exc:
            raise click.ClickException(str(exc)) from exc
        _print_result(result)
    else:
        raise click.UsageError("Provide a SKILL_ID or use --all.")


@skills.command(name="update")
@click.option(
    "--force", is_flag=True, help="Overwrite files even if they have been modified."
)
def update_cmd(force: bool) -> None:
    """Re-install all currently installed skills (picks up new versions)."""
    project_root = find_project_root()

    from kedro_skills.orchestrator import update_skills  # noqa: PLC0415

    results = update_skills(project_root, force=force)
    if not results:
        click.echo("Nothing to update — no skills are installed.")
        return

    for result in results:
        _print_result(result)


@skills.command(name="uninstall")
@click.argument("skill_id")
@click.option(
    "--force", is_flag=True, help="Remove files even if they have been modified."
)
def uninstall_cmd(skill_id: str, force: bool) -> None:
    """Uninstall a skill from the current Kedro project."""
    project_root = find_project_root()

    from kedro_skills.orchestrator import uninstall_skill  # noqa: PLC0415

    try:
        result = uninstall_skill(skill_id, project_root, force=force)
    except KeyError as exc:
        raise click.ClickException(str(exc)) from exc
    _print_result(result)


def _past_tense(operation: str) -> str:
    """Return a friendly past-tense verb for the operation."""
    mapping = {"install": "Installed", "update": "Updated", "uninstall": "Uninstalled"}
    return mapping.get(operation, operation.capitalize() + "ed")


def _print_result(result: object) -> None:
    """Format and print an OperationResult."""
    from kedro_skills.orchestrator import OperationResult  # noqa: PLC0415

    if not isinstance(result, OperationResult):
        return

    if result.refused:
        click.echo(
            f"\n⚠  {result.operation.capitalize()} of '{result.skill_id}' refused — "
            f"the following files have been modified:"
        )
        for d in result.refused:
            status = "deleted" if d.actual_sha256 is None else "modified"
            click.echo(f"     {d.path} ({status})")
        click.echo("   Use --force to overwrite.")
    elif result.written:
        verb = _past_tense(result.operation)
        click.echo(f"✓  {verb} '{result.skill_id}' ({len(result.written)} files)")
    else:
        verb = _past_tense(result.operation)
        click.echo(f"✓  {verb} '{result.skill_id}'")
