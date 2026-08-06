# Developer Guide

## Setup

```bash
git clone https://github.com/kedro-org/kedro-skills.git
cd kedro-skills
pip install -e ".[dev]"
```

## Running checks

```bash
# Individual commands
ruff check src/ tests/
ruff format --check src/ tests/
mypy src/
pytest tests/ -v

# All at once
ruff check src/ tests/ && ruff format --check src/ tests/ && mypy src/ && pytest tests/ -v
```

## Project structure

```
src/kedro_skills/
├── cli.py              # Kedro CLI plugin (kedro skills ...)
├── orchestrator.py     # Coordinates install/update/uninstall across renderers
├── installer.py        # File-writing logic and drift detection
├── registry.py         # Loads skill definitions from registry.yaml
├── state.py            # Tracks installed skills per project
├── utils.py            # Shared helpers
└── renderers/
    ├── agents_md.py    # AGENTS.md block renderer (Codex CLI, Copilot, Cursor)
    ├── cursor.py       # .cursor/rules/*.mdc renderer
    ├── copilot.py      # .github/instructions/*.instructions.md renderer
    ├── claude.py       # .claude/skills/<id>/SKILL.md renderer
    └── _pointer.py     # Shared pointer-line logic

skills/
└── catalog-config/
    └── SKILL.md        # Canonical skill content (Agent Skills standard)

registry.yaml           # Skill metadata: id, category, paths, ide_support
tests/                   # Mirrors src/ — one test module per source module
pyproject.toml           # Build config (hatchling), dependencies, tool settings
```

## How to author a new skill

Before creating a new skill, run `kedro skills list` to check it doesn't overlap
with an existing one.

1. **Create `skills/<id>/SKILL.md`** with Agent Skills frontmatter:
   ```yaml
   ---
   name: my-skill
   description: >-
     What this skill helps with.
   ---
   ```
   Write the skill body below the frontmatter — this is the content that gets
   installed into projects.

2. **Add a registry entry** in `registry.yaml`:
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
   - `paths` — glob patterns that control file-scoped activation (Cursor and Copilot use these to fire the skill only when the user edits matching files).
   - `ide_support` — which renderers to run: `cursor`, `copilot`, `claude`, `codex`.

3. **Test locally:**
   ```bash
   pip install -e .
   kedro skills install my-skill   # run inside a Kedro project
   ```

4. **Verify output** — check that the canonical file, AGENTS.md block, and
   IDE-specific files are all written correctly.

5. See the [Agent Skills standard](https://agentskills.io/) for the full spec.

## Releasing

1. Create a release branch:
   ```bash
   git checkout -b release/<version>
   ```
2. Bump `version` in `pyproject.toml`.
3. Update `RELEASE.md` with highlights for the new version.
4. Open a PR from `release/<version>` to `main`, get it reviewed and merged.
5. `publish.yml` detects the new version on `main`, builds, and publishes to
   PyPI automatically.
6. Verify in a fresh environment:
   ```bash
   pip install kedro-skills==<version>
   ```

## CI

| Workflow | Trigger | What it does |
|----------|---------|-------------|
| `ci.yml` | Push to `main` + PRs | Lint, type-check, tests (3.10–3.14), build sdist+wheel |
| `publish.yml` | Push to `main` | Checks if version is new on PyPI → build → publish → GitHub release from `RELEASE.md` |

### Required repo secrets

| Secret | Purpose | Where to get it |
|--------|---------|-----------------|
| `PYPI_TOKEN` | Upload packages to PyPI | https://pypi.org/manage/account/token/ (scoped to `kedro-skills`) |
| `GH_TAGGING_TOKEN` | Create tags and GitHub releases | GitHub PAT with `contents: write` scope |
