# Skill evals

This directory runs each skill's guidance against several LLMs using promptfoo. Every test runs twice, once with the skill in the prompt (with-skill) and once without it (baseline), so you can see what the skill changes. Each test combines deterministic JS assertions on the generated code blocks with llm-rubric checks graded by a judge model.

The evals measure whether models follow a skill. They can't tell you whether the skill itself is right.

## Requirements

- Node >= 22.22 (promptfoo 0.123.1 requires it; install via `nvm install 22`)
- Python on PATH (used by `fixture/context.py` to build the project context variable)
- API keys for the models you run. The default judge is OpenAI's `gpt-4o-mini`, so without an OpenAI key, pick another judge with `EVAL_JUDGE` (see below).
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

To run only the models you have keys for, filter by provider id. To grade with a different judge, set `EVAL_JUDGE` to a promptfoo provider id:

```bash
make eval-skill SKILL=parameters-and-config \
  ARGS="--filter-providers claude" \
  EVAL_JUDGE=anthropic:messages:claude-haiku-4-5-20251001
```

The Anthropic providers in `parameters-and-config` are commented out for now; uncomment them in its `promptfooconfig.yaml` to run this example.

`EVAL_JUDGE` overrides the judge set in each suite's `defaultTest.options.provider`. A judge from the same model family as the model under test tends to favour its answers, so use a different family where you can.

## Reading the results

The terminal prints a table with one row per test and one column per prompt and provider. For more detail, open the web viewer:

```bash
npx promptfoo@0.123.1 view
```

It runs at `http://localhost:15500` and shows the full responses, every assertion with the judge's reasoning, and past runs, which promptfoo keeps in `~/.promptfoo`. To save a report, add `-o results.html` or `-o results.json` to `ARGS`.

A test that passes with the skill and fails on baseline shows what the skill fixes. If it fails both, the model ignored the skill. If it passes both, the skill isn't needed for that case, but the test still catches a skill that makes the answer worse.

`make eval` and `make eval-skill` exit non-zero only when a with-skill test fails or errors; baseline failures are expected and don't count. After the promptfoo table, `evals/lib/gate.js` prints the with-skill failures and how many baseline results passed. The full results are saved to `evals/results/<skill>.json` (git-ignored; override the directory with `EVAL_RESULTS=path`).

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
5. Use `forbid()` from `lib/blocks.js` for deterministic checks (it only looks at code blocks and skips blocks introduced by a line like "Do not use:", so explaining a wrong pattern does not fail) and add an `llm-rubric`.
6. Run with `ARGS="--filter-providers gpt-4o"`. Tests that fail on baseline show what the skill fixes. A test the baseline passes is still worth keeping: it catches a skill that makes the answer worse, for example by stating a wrong rule.
7. If a model labels code blocks in a format `blocks.js` misses, add a case to `lib/blocks.test.js`.

## Refreshing the fixture

The snapshot is committed, so it only changes when someone refreshes it. `evals/fixture/refresh.sh` scaffolds the starter from the latest Kedro release and records the version it used in `STARTER_VERSION`. To use a specific release instead:

```bash
KEDRO_VERSION=x.y.z evals/fixture/refresh.sh
```

Review the diff before committing.