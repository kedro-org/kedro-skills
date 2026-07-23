# kedro-skills

[![Python Version](https://img.shields.io/badge/python-3.10%20%7C%203.11%20%7C%203.12%20%7C%203.13%20%7C%203.14-blue.svg)](https://pypi.org/project/kedro-skills/)
[![License](https://img.shields.io/badge/license-Apache%202.0-blue.svg)](LICENSE)

Distribute AI coding skills to Kedro projects.

## Installation

```bash
# From the repository root:
pip install .

# Or in editable/development mode:
pip install -e ".[dev]"
```

## Quick start

```bash
# Inside a Kedro project:
kedro skills list
kedro skills install catalog-config       # prompts for IDE selection
kedro skills install catalog-config --ide cursor  # non-interactive
kedro skills update
kedro skills uninstall catalog-config
```

### CLI commands

| Command | Description |
|---------|-------------|
| `kedro skills list` | Show available skills and their install status |
| `kedro skills install <id>` | Install a skill (prompts for IDE selection) |
| `kedro skills install <id> --ide cursor,claude` | Install for specific IDEs (no prompt) |
| `kedro skills install --all` | Install all available skills for all IDEs |
| `kedro skills install --force` | Overwrite even if files were modified |
| `kedro skills update` | Re-install all installed skills (picks up new versions) |
| `kedro skills update --force` | Overwrite modified files during update |
| `kedro skills uninstall <id>` | Remove a skill from the project |
| `kedro skills uninstall --force` | Remove even if files were modified |

> **Tip:** For CI/scripts, always pass `--ide` or `--all` to avoid the interactive prompt.

### Manual testing

```bash
# Install kedro-skills from source (in the kedro-skills repo root)
pip install .

# Create a test Kedro project
pip install kedro
kedro new --name test-project -s spaceflights-pandas
cd test-project

# Install a skill (will prompt for IDE selection — press Enter for all)
kedro skills list
kedro skills install catalog-config
# Expected prompt: "Available IDEs for 'catalog-config': cursor, copilot, claude"
#                  "Install for which IDEs? [all]:"

# Inspect the output
ls .agents/skills/catalog-config/SKILL.md
cat AGENTS.md
ls .cursor/rules/
ls .github/instructions/
ls .claude/skills/catalog-config/

# Verify idempotency (no errors on re-run)
kedro skills install catalog-config --ide cursor,copilot,claude

# Verify drift detection
echo "modified" > .cursor/rules/catalog-config.mdc
kedro skills update          # should refuse with file path
kedro skills update --force  # should overwrite

# Verify uninstall
kedro skills uninstall catalog-config
kedro skills list            # should show "not installed"
```

## Development

```bash
pip install -e ".[dev]"
ruff check src/ tests/ && ruff format --check src/ tests/ && mypy src/ && pytest tests/ -v
```
