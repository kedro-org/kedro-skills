# Upcoming Release

## Major features and improvements

## Bug fixes and other changes

## Community contributions

# Release 0.1.0

## What is `kedro-skills`?

A PyPI package that distributes AI coding skills to Kedro projects. One command
installs contextual guidance that activates automatically when your AI assistant
edits matching files — across Cursor, GitHub Copilot, Claude Code, and Codex CLI.

## Highlights

- `kedro skills install catalog-config` — installs the catalog configuration
  skill with full file layout across all supported IDEs.
- `kedro skills list` — shows available skills and their install status.
- `kedro skills update` — re-renders all installed skills after a package upgrade.
- `kedro skills uninstall <id>` — clean removal of all managed files.
- Drift detection — warns when hand-edited files would be overwritten.
- Block-aware AGENTS.md management — user content outside managed blocks is preserved.

## Supported IDEs

- Cursor (`.cursor/rules/*.mdc`)
- GitHub Copilot (`.github/instructions/*.instructions.md`)
- Claude Code (`.claude/skills/<id>/SKILL.md`)
- Codex CLI (`AGENTS.md`)

## Skills included

- `catalog-config` — Kedro data catalog configuration guidance for `conf/**/*.yml` files.
