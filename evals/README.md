# Skill evals

This directory runs each skill's guidance against several LLMs using promptfoo. Every test runs twice, once with the skill in the prompt (with-skill) and once without it (baseline), so you can see what the skill changes. Each test combines deterministic JS assertions on the generated code blocks with llm-rubric checks graded by a judge model.

The evals measure whether models follow a skill. They can't tell you whether the skill itself is right.

## Requirements

- Node >= 22.22 (promptfoo 0.123.1 requires it; install via `nvm install 22`)
- Python on PATH (used by `fixture/context.py` to build the project context variable)
- API keys: `ANTHROPIC_API_KEY` and `OPENAI_API_KEY` (OpenAI is also used by the judge, `gpt-4o-mini`)
- `uv` is only needed to refresh the fixture

`npx` fetches promptfoo on the first run, so there's nothing to install.

## Setup

Put your keys in `evals/.env` (git-ignored) as `KEY=value` lines, or export them in your shell. The Makefile passes `evals/.env` with `--env-file` when the file exists. Override the path with `EVAL_ENV=path`.

## Running

```bash
make eval-test                    # parser unit tests, no API calls
make eval-skill SKILL=parameters-and-config
make eval                         # all suites
```

Pass extra promptfoo flags through `ARGS`. Examples:

```bash
make eval ARGS="--filter-providers gpt-4o"
make eval ARGS="--filter-first-n 2"
make eval ARGS="--filter-pattern 'credentials'"
make eval ARGS="--no-cache"
```

promptfoo caches responses; use `--no-cache` after changing prompts or tasks. Avoid `$` in `ARGS` because Make expands it.

## Reading the results

The terminal prints a table with one row per test and one column per prompt and provider. For more detail, open the web viewer:

```bash
npx promptfoo@0.123.1 view
```

It runs at `http://localhost:15500` and shows the full responses, every assertion with the judge's reasoning, and past runs, which promptfoo keeps in `~/.promptfoo`. To save a report, add `-o results.html` or `-o results.json` to `ARGS`.

A useful test passes with the skill and fails on baseline. If it fails both, the model ignored the skill. If it passes both, the test isn't measuring the skill. `make` exits non-zero whenever any assertion fails, including the expected baseline failures, so read the table rather than the exit code.

## Layout

```
evals/
├── fixture/
│   ├── project/              # committed snapshot of spaceflights-pandas starter text files
│   ├── refresh.sh
│   ├── STARTER_VERSION
│   └── context.py            # builds project context from a test's project_files
├── lib/
│   ├── blocks.js             # code-block parsing helpers
│   └── blocks.test.js
├── prompts/
│   ├── with-skill.json
│   └── baseline.json
└── skills/
    └── <id>/
        ├── promptfooconfig.yaml
        └── assertions.js
```

Suites live here rather than under `skills/` because `skills/` is packaged into the wheel.

## Adding a suite for a skill

1. Copy `evals/skills/parameters-and-config/` to `evals/skills/<id>/` and point `skill_content` at the new `SKILL.md`.
2. Write one test per rule in the `SKILL.md`.
3. Write tasks where the user asks for the wrong thing, for example "set up TemplatedConfigLoader", and leave out fixture files that already show the right pattern. Neutral tasks tend to pass even without the skill.
4. Set `project_files` as a comma-separated string, not a YAML list (promptfoo turns lists into one test per item).
5. Use `forbid()` from `lib/blocks.js` for deterministic checks (it only looks at code blocks, so explaining a wrong pattern does not fail) and add an `llm-rubric`.
6. Run with `ARGS="--filter-providers gpt-4o"` and confirm each test fails on baseline.
7. If a model labels code blocks in a format `blocks.js` misses, add a case to `lib/blocks.test.js`.

## Refreshing the fixture

The snapshot is committed, so it only changes when someone refreshes it. `evals/fixture/refresh.sh` scaffolds the starter from the latest Kedro release and records the version it used in `STARTER_VERSION`. To use a specific release instead:

```bash
KEDRO_VERSION=x.y.z evals/fixture/refresh.sh
```

Review the diff before committing.