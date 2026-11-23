# Skill evals

This directory checks whether LLMs follow a skill's guidance, using [promptfoo](https://www.promptfoo.dev/). Every test runs twice, once with the skill in the prompt (with-skill) and once without it (baseline), which shows what the skill changes.

The evals measure whether models follow a skill. They can't tell you whether the skill itself is right.

## How it works

A test is one task plus a few files from the fixture project in `evals/fixture/project/`, listed in `project_files`. promptfoo sends the task and files to each provider twice: once inside the with-skill prompt that includes the skill's `SKILL.md`, and once inside the baseline prompt without it. JavaScript checks in the suite's `assertions.js` and an `llm-rubric` judge grade the answers.

```yaml
- description: Refuse a removed config loader when asked for it
  vars:
    project_files: pyproject.toml
    task: >-
      I want to share a bucket name across catalog files with ${bucket}
      style templating. Set the project up to use TemplatedConfigLoader with
      a globals.yml file.
  assert:
    - type: javascript
      value: file://assertions.js:noRemovedConfigLoaders
    - type: llm-rubric
      value: >-
        Tells the user that TemplatedConfigLoader was removed (in Kedro
        0.19) and does not configure it. Uses OmegaConfigLoader instead.
```

The task deliberately asks for something outdated, so a model without the skill tends to get it wrong.

## Quick start

1. Check Node and Python.
   Run `make eval-check-node`. If it fails, install the latest Node 22 with `nvm install 22` and switch to it. Python must be on PATH because `fixture/context.py` uses it to build the project context.
2. Add your API key.
   Create `evals/.env` (git-ignored) containing `OPENAI_API_KEY=<your key>`, or export the variable in your shell. The default suite uses `gpt-4o` and the default judge uses `gpt-4o-mini`, both OpenAI, so one OpenAI key is enough to run the example suite out of the box.
3. Verify the setup.
   Run `make eval-test`. This runs the harness's own unit tests and makes no API calls, so it checks your setup for free.
4. Run a cheap first evaluation.
   Run `make eval-skill SKILL=kedro-parameters-and-config ARGS="--filter-first-n 2"`. This runs only the first two tests instead of the whole suite.
5. View the results.
   Run `npx promptfoo@0.123.1 view` to open the web viewer at `http://localhost:15500`. See [Reading the results](#reading-the-results) for what the columns mean.

Nothing needs to be installed globally because `npx` fetches promptfoo on first run. `uv` is only needed if you refresh the fixture.

Every test makes one with-skill call and one baseline call per provider, plus judge calls for each llm-rubric assertion. Cost grows with the number of tests times the number of providers. Filter with `--filter-first-n`, `--filter-providers`, or `--filter-pattern` while iterating.

## Running

```bash
make eval-test                    # parser unit tests, no API calls
make eval-skill SKILL=kedro-parameters-and-config
make eval                         # all suites
make eval-config CONFIG=evals/skills/<dir>/compare.yaml
```

Pass extra promptfoo flags through `ARGS`. Examples:

```bash
make eval ARGS="--filter-providers gpt-4o"
make eval ARGS="--filter-first-n 2"
make eval ARGS="--filter-pattern 'credentials'"
make eval ARGS="--no-cache"
```

promptfoo caches responses. Use `--no-cache` after changing prompts or tasks. Avoid `$` in `ARGS` because Make expands it.

`--filter-providers` takes a pattern matched against provider ids, so `ARGS="--filter-providers claude"` runs only the Claude models (after you enable them in the suite's `promptfooconfig.yaml`).

`make eval-config` runs a config that isn't a suite's `promptfooconfig.yaml`, such as one comparing skill variants (see [Variants of one skill](#variants-of-one-skill)).

`EVAL_ENV` changes the env file path (default `evals/.env`). `EVAL_RESULTS` changes the output directory (default `evals/results`).

## Choosing models

Models under test are the `providers` list in each suite's `promptfooconfig.yaml`. A provider id has the form `<provider>:<model>`. Each provider reads its key from an environment variable that you put in `evals/.env`.

| Provider | Example id | Key | Docs |
| --- | --- | --- | --- |
| OpenAI | `openai:chat:gpt-4o` | `OPENAI_API_KEY` | [OpenAI](https://www.promptfoo.dev/docs/providers/openai/) |
| Anthropic | `anthropic:messages:claude-sonnet-5-5` | `ANTHROPIC_API_KEY` | [Anthropic](https://www.promptfoo.dev/docs/providers/anthropic/) |
| Google Gemini | `google:gemini-3.8-flash` | `GOOGLE_API_KEY` (or `GEMINI_API_KEY`) | [Google AI Studio](https://www.promptfoo.dev/docs/providers/google/) |
| OpenRouter | `openrouter:<org>/<model>` | `OPENROUTER_API_KEY` | [OpenRouter](https://www.promptfoo.dev/docs/providers/openrouter/) |
| Ollama (local, no key) | `ollama:chat:qwen3` | none | [Ollama](https://www.promptfoo.dev/docs/providers/ollama/) |

promptfoo's [providers page](https://www.promptfoo.dev/docs/providers/) lists Azure OpenAI, AWS Bedrock, Vertex AI, and many others. Model names change often, so check the provider's page for current ones. OpenRouter gives access to models from many vendors with a single key.

To add a model, add an entry to the `providers` list in the suite config:

```yaml
providers:
  - id: openai:chat:gpt-4o
    config: { temperature: 0, max_tokens: 4096 }
  - id: anthropic:messages:claude-sonnet-5-5
    config: { temperature: 0, max_tokens: 4096 }
```

`temperature: 0` keeps answers as repeatable as the model allows, which makes runs easier to compare.

Reasoning models may reject temperature settings and count reasoning tokens against the limit. See the provider page for details. To run a subset of providers without editing the file, pass `--filter-providers`.

### Judge

The default judge is `gpt-4o-mini`, set in `defaultTest.options.provider`. Override it with `EVAL_JUDGE`:

```bash
make eval-skill SKILL=kedro-parameters-and-config \
  EVAL_JUDGE=anthropic:messages:claude-haiku-5-5
```

A judge from the same model family as the model under test tends to favour its answers, so use a different family where you can. The judge needs its own key too. See promptfoo's [llm-rubric docs](https://www.promptfoo.dev/docs/configuration/expected-outputs/model-graded/llm-rubric/) for how grading works.

## Reading the results

The terminal prints a table with one row per test and one column per prompt and provider. For more detail, open the web viewer:

```bash
npx promptfoo@0.123.1 view
```

It runs at `http://localhost:15500` and shows the full responses, every assertion with the judge's reasoning, and past runs, which promptfoo keeps in `~/.promptfoo`. To save a report, add `-o results.html` or `-o results.json` to `ARGS`.

A test that passes with the skill and fails on baseline shows what the skill fixes. If it fails both, the model ignored the skill. If it passes both, the skill isn't needed for that case, but the test still catches a skill that makes the answer worse.

`make eval` and `make eval-skill` exit non-zero only when a with-skill test fails or errors; baseline failures are expected and don't count. After the promptfoo table, `evals/lib/gate.js` prints the with-skill failures and how many baseline results passed. promptfoo saves the full results to `evals/results/<skill>.json` (override the directory with `EVAL_RESULTS=path`).

## Adding a suite for a skill

1. Copy `evals/skills/kedro-parameters-and-config/` to `evals/skills/<id>/` and point `skill_content` at the new `SKILL.md`.
2. Write one test per rule in the `SKILL.md`.
3. Write tasks where the user asks for the wrong thing, for example "set up TemplatedConfigLoader", and leave out fixture files that already show the right pattern. Neutral tasks tend to pass even without the skill.
4. Set `project_files` as a comma-separated string, not a YAML list (promptfoo turns lists into one test per item).
5. Use `forbid()` from `lib/blocks.js` for deterministic checks, and add an `llm-rubric`. `forbid()` only looks at code blocks and skips blocks introduced by a line like "Do not use:", so explaining a wrong pattern does not fail.
6. Run with `ARGS="--filter-first-n 2"` or `--filter-providers` to keep it cheap while iterating. Tests that fail on baseline show what the skill fixes. A test the baseline passes is still worth keeping: it catches a skill that makes the answer worse, for example by stating a wrong rule.
7. If a model labels code blocks in a format `blocks.js` misses, add a case to `lib/blocks.test.js`.
8. Unit-test the suite's own JS checks against hand-written good and bad answers in `evals/skills/<dir>/*.test.js`. `make eval-test` runs them alongside the `lib/` tests.

### Variants of one skill

To compare two versions of a skill on identical tasks, put the shared tests in a directory without a `promptfooconfig.yaml`, so `make eval` skips it. Load them from each variant's config with `tests: file://../<shared-dir>/tests.yaml`, changing only `skill_content`. Label the prompts `with-skill:<variant>`: `gate.js` treats any such label as with-skill, so a failure in either variant fails the run. To run a combined config with one prompt column per variant:

```bash
make eval-config CONFIG=evals/skills/<shared-dir>/compare.yaml
```

## Refreshing the fixture

The snapshot is committed, so it only changes when someone refreshes it. `evals/fixture/refresh.sh` scaffolds the starter from the latest Kedro release and records the version it used in `STARTER_VERSION`. To use a specific release instead:

```bash
KEDRO_VERSION=x.y.z evals/fixture/refresh.sh
```

Review the diff before committing.

## Layout

```text
evals/
├── fixture/
│   ├── project/              # committed snapshot of spaceflights-pandas starter text files
│   ├── refresh.sh
│   ├── STARTER_VERSION
│   ├── context.py            # builds project context from a test's project_files
│   └── test_context.py
├── lib/
│   ├── blocks.js             # code-block parsing helpers
│   ├── blocks.test.js
│   ├── gate.js               # exit code from with-skill results only
│   └── gate.test.js
├── prompts/
│   ├── with-skill.json
│   └── baseline.json
└── skills/
    └── <id>/
        ├── promptfooconfig.yaml
        └── assertions.js
```

Suites live here rather than under `skills/` because `skills/` is packaged into the wheel.

## Troubleshooting

- "Skill evals need Node >= 22.22" means your Node is too old. Upgrade with `nvm install 22` or your system package manager.
- An API key error means the key isn't in `evals/.env` or your shell. Add it, or skip that provider with `--filter-providers`.
- If results look stale after you edit a prompt or task, add `--no-cache` to `ARGS`.
- If every test errors, including the JS checks, check the judge's key. Without it promptfoo can't grade the test at all. Set the key, or pick a judge you have a key for with `EVAL_JUDGE`.
