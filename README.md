# kedro-skills

[![Python Version](https://img.shields.io/badge/python-3.10%20%7C%203.11%20%7C%203.12%20%7C%203.13%20%7C%203.14-blue.svg)](https://pypi.org/project/kedro-skills/)
[![PyPI Version](https://img.shields.io/pypi/v/kedro-skills.svg)](https://pypi.org/project/kedro-skills/)
[![License](https://img.shields.io/badge/license-Apache%202.0-blue.svg)](LICENSE)

Distribute AI coding skills to Kedro projects. One command installs contextual
guidance that activates automatically when your AI assistant edits matching
files — across Cursor, GitHub Copilot, Claude Code, and Codex CLI.

## Installation

```bash
pip install kedro-skills
```

## Quick start

```bash
# Inside any Kedro project:
kedro skills list
kedro skills install catalog-config
```

This writes managed files into your project. They should be committed to git so
the whole team benefits.

## What it writes

```
my-kedro-project/
├── .agents/skills/catalog-config/SKILL.md              # canonical (Agent Skills standard)
├── AGENTS.md                                           # content discovery (Cursor, Copilot, Codex CLI)
├── .cursor/rules/catalog-config.mdc                    # glob-scoped activation (Cursor)
├── .github/instructions/catalog-config.instructions.md # glob-scoped activation (Copilot)
└── .claude/skills/catalog-config/SKILL.md              # Claude Code (inline copy, always discoverable)
```

`AGENTS.md` is the content-discovery channel — one file reaches Cursor, Copilot,
and Codex CLI. `.cursor/rules/` and
`.github/instructions/` add glob-scoped activation so the skill fires only when
editing matching files, not on every prompt.

## CLI reference

| Command | Description |
|---------|-------------|
| `kedro skills list` | Show available skills and their install status |
| `kedro skills install <id>` | Install a skill for all supported IDEs |
| `kedro skills install --all` | Install every available skill |
| `kedro skills install --ide cursor,claude` | Restrict to specific IDEs |
| `kedro skills install --force` | Overwrite even if files were hand-edited |
| `kedro skills update` | Re-render all installed skills (picks up package upgrades) |
| `kedro skills update --force` | Overwrite modified files during update |
| `kedro skills uninstall <id>` | Remove a skill and all its managed files |
| `kedro skills uninstall --force` | Remove even if files were hand-edited |

## How to author a new skill

Before creating a new skill, run `kedro skills list` to check it doesn't overlap
with an existing one.

1. Create `skills/<id>/SKILL.md` with Agent Skills frontmatter:
   ```yaml
   ---
   name: my-skill
   description: >-
     What this skill helps with.
   ---
   ```
2. Add a registry entry in `registry.yaml`:
   ```yaml
   skills:
     - id: my-skill
       category: core
       description: >-
         What this skill helps with.
       paths:
         - "src/**/*.py"
       ide_support:
         - cursor
         - copilot
         - claude
         - codex
   ```
3. Install in dev mode and test:
   ```bash
   pip install -e .
   kedro skills install my-skill
   ```

See the [Agent Skills standard](https://agentskills.io/) for the full spec.

## IDE-specific notes

- **Claude Code:** Reads `.claude/skills/<id>/SKILL.md` directly. The skill is always discoverable (no `paths:` scoping in the Claude copy). If you want `AGENTS.md` content in Claude sessions too, add `@AGENTS.md` to a `CLAUDE.md` file.
- **Cursor:** `.cursor/rules/*.mdc` fires only when editing files matching `globs:` patterns.
- **GitHub Copilot:** `.github/instructions/*.instructions.md` fires only when editing files matching `applyTo:` patterns.
- **Codex CLI:** Reads `AGENTS.md` natively. Skill block is always active.

## How to try it out

```bash
# Install kedro-skills from source (in the kedro-skills repo root)
pip install .

# Create a test Kedro project
pip install kedro
kedro new --name test-project -s spaceflights-pandas
cd test-project

# See what's available
kedro skills list

# Install the catalog-config skill
kedro skills install catalog-config

# Check what was written
ls .agents/skills/catalog-config/SKILL.md
cat AGENTS.md
ls .cursor/rules/
ls .github/instructions/
ls .claude/skills/catalog-config/

# Running install again is safe — nothing changes
kedro skills install catalog-config --ide cursor,copilot,claude

# If you hand-edit a managed file, update will let you know
echo "modified" > .cursor/rules/catalog-config.mdc
kedro skills update          # refuses and names the modified file
kedro skills update --force  # overwrites your edit with the managed version

# Clean removal when you no longer need a skill
kedro skills uninstall catalog-config
kedro skills list            # back to "not installed"
```

## Development

```bash
pip install -e ".[dev]"
ruff check src/ tests/ && ruff format --check src/ tests/ && mypy src/ && pytest tests/ -v
```

## Links

- [Agent Skills standard](https://agentskills.io/)
- [Kedro docs](https://docs.kedro.org)
