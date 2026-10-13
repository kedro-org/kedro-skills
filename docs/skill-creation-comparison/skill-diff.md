# testing-pipelines: raw vs skill-creator, side by side

A record of how the two versions of the skill differ, for the skill-authoring discussion. Line references are to the iteration 1 files, kept in [v1/](v1/): `raw:` is [`v1/testing-pipelines-raw.md`](v1/testing-pipelines-raw.md), `sc:` is [`v1/testing-pipelines-skill-creator.md`](v1/testing-pipelines-skill-creator.md). Both skills were changed in iteration 2 (see the README); this record compares the versions that were evaluated in rounds 1 and 2. Method and results: [README.md](README.md).

## At a glance

| | raw | skill-creator |
|---|---|---|
| Lines | 211 | 202 |
| Words | 883 | 1014 |
| Code blocks | 10 | 7 |
| Headings (## + ###) | 10 (6 + 4) | 8 (6 + 2) |
| Frontmatter description | 4 lines, factual | 8 lines, "pushy" (lists trigger phrasings) |
| Style | Example-led; uses `# WRONG` / `# Correct` pairs and a dedicated wrong-APIs code block | Explanation-led; says why; uses a "Don't write / Write" table |
| All-caps MUST/NEVER | none | none |

Both were written from the same verified fact sheet (`docs/skill-creation-comparison/facts.md`).

## Frontmatter description

raw:

> Kedro testing guidance for tests/**/*.py in a Kedro project. Use when writing unit tests for node functions, pipeline tests with DataCatalog, MemoryDataset and SequentialRunner, or KedroSession smoke tests. Adds nothing for tests that do not touch Kedro.

skill-creator:

> How to write tests for a Kedro 1.x project in tests/**/*.py, covering unit tests for node functions, in-memory pipeline tests with DataCatalog, MemoryDataset and SequentialRunner, and KedroSession smoke tests. Use this whenever you write, fix or review a test that imports kedro or a Kedro project's nodes and pipelines, even when the request is just "add tests for this pipeline" or "why does my pipeline test fail". Kedro 1.x changed what runners return and how sessions start, and older examples get both wrong. Not needed for tests that never touch Kedro.

- raw says "Adds nothing for tests that do not touch Kedro"; sc says "Not needed for tests that never touch Kedro".
- sc is longer and lists trigger phrases ("write, fix or review", "add tests for this pipeline", "why does my pipeline test fail").
- sc mentions why Kedro 1.x needs care: "Kedro 1.x changed what runners return and how sessions start, and older examples get both wrong."

## Structure

| raw heading | sc heading | notes |
|---|---|---|
| # Testing Kedro Nodes and Pipelines | # Writing tests for a Kedro project | Both are H1 titles |
| ## Pick the right kind of test | ## Choose the smallest test that answers the question | raw uses a table; sc uses a numbered list with rationale |
| ## Unit-testing a node | ## 1. Node unit tests | sc numbers the test-type sections |
| ## Testing a pipeline in memory | ## 2. In-memory pipeline tests | |
| ### The runner returns datasets, not data | (part of 2.) | sc covers this as a bold paragraph inside the pipeline-test section |
| ### Provide every free input, including `params:` | (part of 2.) | sc covers free inputs and params as bold paragraphs inside the pipeline-test section |
| ### Testing part of a pipeline | ### Running part of a pipeline | Same level; sc says "Running" instead of "Testing" |
| ## Smoke-testing the whole project | ## 3. KedroSession smoke tests | |
| ### Test environments and runtime parameters | ### Test environments and runtime parameters | Identical heading text and level |
| ## Wrong APIs: do not generate these | ## Imports and APIs that do not exist in Kedro 1.x | raw uses a code block; sc uses a two-column table |
| ## Fixtures and layout | ## Project layout | raw mixes fixtures and layout; sc keeps layout separate and discusses fixtures earlier |

## Fact by fact

| Fact | raw | skill-creator | Difference |
|---|---|---|---|
| No pytest plugin or fixtures | raw:L11-13: "Kedro ships **no pytest plugin and no fixtures**. Every fixture you use (`catalog`, `session`, sample data) must be defined in your own test module or `conftest.py`." | sc:L19-22: "Kedro ships no pytest plugin, so there are no `kedro_session`, `kedro_context` or `catalog` fixtures. If a test needs one, define it in the test module or in `tests/conftest.py`. A test that asks for a fixture nobody defined fails at collection." | sc names specific fixtures and notes collection failure. |
| Choosing the test layer | raw:L15-23: table ("What you are checking / Test type / Needs Kedro objects?"). Ends with "Prefer the first two. Never start a `KedroSession` to test a single node." | sc:L24-35: numbered list. "Each layer up costs more and fails for more reasons, so test at the lowest layer that can catch the bug." | raw uses a table; sc uses a numbered list with cost/frailty rationale. |
| Node unit test calls function directly | raw:L25-27: "A node is a plain Python function. Call it directly." | sc:L29-30: "Node logic → call the node function directly. Nodes are plain Python functions, so a unit test needs no catalog, runner or session." | sc adds that no Kedro objects are needed. |
| Params passed as plain dict in unit tests | raw:L46: "Pass parameters as the plain dict the node receives. There is no `params:` here." | sc:L53-54: "The node receives parameters as a plain dict, so pass a dict. The `params:` prefix only exists in pipeline wiring." | sc explicitly separates node params from pipeline wiring. |
| DataCatalog + MemoryDataset + SequentialRunner | raw:L50-51: "Build a `DataCatalog` of `MemoryDataset`s and run with `SequentialRunner`." | sc:L59-60: shows imports and usage in code under section "2. In-memory pipeline tests". | raw states it as upfront prose; sc relies on code and section title. |
| catalog[name] = df wraps in MemoryDataset | raw:L72-73: "`catalog["model_input_table"] = df` is equivalent: raw data is wrapped in a `MemoryDataset` for you." | sc:L78-79: "`catalog["model_input_table"] = df` also works. Raw data is wrapped in a `MemoryDataset` for you." | Nearly identical wording. |
| Runner returns datasets, requires .load() | raw:L75-78: "In Kedro 1.x, `runner.run(...)` returns `{output_name: dataset}` for the pipeline's outputs. Call `.load()` on the value, or use `catalog.load(name)`." Code block at raw:L80-86 shows `# WRONG` indexing and `# Correct` .load(). | sc:L83-88: "**The runner returns datasets, not data.** ... Pre-1.0 runners returned the data itself, so older examples index straight into the result... On 1.x that fails because the value is a `MemoryDataset`." | raw uses a Correct/Wrong code pair; sc explains the 1.x change and why old examples fail. |
| session.run() also returns datasets | not stated | sc:L150: "`session.run()` also returns `{name: dataset}`, same as the runner." | only in sc |
| Missing free input raises ValueError; use pipeline.inputs() | raw:L90-92: "The runner raises `ValueError: Pipeline input(s) {...} not found in the DataCatalog` for any free input not in the catalog. Use `pipeline.inputs()` to list them." | sc:L90-92: "Every free input must be in the catalog. Otherwise the run stops with `ValueError: Pipeline input(s) {...} not found in the DataCatalog`. `pipeline.inputs()` tells you exactly what to provide." | sc uses "tells you exactly what to provide"; raw uses "to list them". |
| Literal `params:` key in catalog | raw:L95-100: comment block with `# Correct` and `# WRONG` examples. | sc:L94-96: "Parameters are registered under their literal input name. If a node declares `"params:model_options"`, the catalog key is `"params:model_options"`. Registering `"model_options"` leaves the input missing." | raw uses code comments; sc uses prose with conditional logic. |
| Intermediates released after last consumer; use to_outputs workaround | raw:L102-106: "It also **releases** intermediates once their last consumer has run, so `catalog.load("X_train")` after the run raises `DatasetError`. Only free inputs and pipeline outputs survive. To assert on an intermediate, slice so that it becomes an output (next section)." | sc:L98-103: "... then releases each one once its last consumer has run. So `catalog.load("X_train")` after the run raises `DatasetError: ... has not been saved yet`. ... To check an intermediate, end the pipeline there so it becomes an output:" | sc adds the detailed error suffix and uses "end the pipeline there". |
| Slicing methods list | raw:L121-122: "Available: `only_nodes`, `from_nodes`, `to_nodes`, `from_inputs`, `to_outputs`, `only_nodes_with_tags`, `filter`." | sc:L111-112: "`only_nodes`, `from_nodes`, `to_nodes`, `from_inputs`, `to_outputs`, `only_nodes_with_tags` and `filter` return a new `Pipeline`." | raw lists as "Available"; sc notes they return a new Pipeline. |
| Slice inputs | raw:L113-114: `pipeline = ...; # pipeline.inputs() == {...}` | sc:L116-117: `sliced = ...; assert sliced.inputs() == {...}` | raw uses a comment; sc uses an assert. |
| MemoryDataset copies DataFrames | not stated | sc:L120-121: "`MemoryDataset` copies pandas DataFrames and numpy arrays on load and save, so a node that mutates its input cannot corrupt the fixture between tests." | only in sc |
| bootstrap_project required (and why) | raw:L136: `# required, before KedroSession.create`. raw:L141-142: "Without `bootstrap_project`, `create` fails with `ValueError: Package name not found`." | sc:L135: `bootstrap_project(PROJECT_PATH)`. sc:L142-144: "`bootstrap_project` reads `pyproject.toml` and registers the project's package and settings. Without it, `KedroSession.create` fails with `ValueError: Package name not found`." | raw puts "required" in a code comment; sc explains it reads pyproject.toml. |
| Project path from `__file__`, not cwd | raw:L132: `PROJECT_PATH = Path(__file__).resolve().parents[1]  # project root, not cwd` | sc:L131: `PROJECT_PATH = Path(__file__).resolve().parents[1]`. sc:L145-146: "Resolve the project root from `__file__`. The starter template uses `Path.cwd()`, which only works when pytest runs from the project root." | raw notes "not cwd" in comment; sc explains the starter template anti-pattern. |
| Smoke tests write real files to `data/` | raw:L143-145: "This uses the real `conf/base/catalog.yml` and **writes real files** to `data/`. Keep these tests few, and point the catalog elsewhere through a test env if that matters." | sc:L33-35: "It reads the real `conf/` and writes real files to `data/`, so keep it to one or two tests." | raw mentions redirecting via test env; sc quantifies "one or two". |
| One run per session | raw:L146: "One session = one run. A second `session.run()` raises `KedroSessionError`." | sc:L148-149: "A session runs once. A second `session.run()` raises `KedroSessionError`, so create a new session per run." | sc adds explicit instruction to create a new session per run. |
| `pipeline_name=` deprecated | raw:L147: "`pipeline_name=` is deprecated. Use `pipeline_names=[...]`." | sc:L147: "Use `pipeline_names=[...]`. `pipeline_name=` is deprecated." | Same content, reversed order. |
| `runtime_params` must be nested | raw:L159-161: "`runtime_params` must be **nested**. A dotted key like `{"model_options.test_size": 0.5}` is not expanded. It becomes a literal key and the real value is unchanged. (Only the CLI `--params` parses dots.)" | sc:L164-166: "`runtime_params` must be nested. Through the Python API, a dotted key like `{"model_options.test_size": 0.5}` is stored as a literal key and the real value is unchanged. Only the CLI's `--params` splits on dots." | sc notes "Through the Python API". |
| Misspelled or missing `env` is silent | raw:L162: "A misspelled or missing `env` is **not** an error. Kedro silently uses base only." | sc:L167-168: "A missing env is silent. `env="tset"` raises nothing and you get base config, so a typo turns a test-config test into a production-config test." | sc gives a concrete typo example and consequence. |
| Env `parameters.yml` replaces whole top-level keys | raw:L163-164: "A `parameters.yml` in the test env **replaces** whole top-level keys from `base`. Repeat every sibling key you still need." | sc:L169-171: "An env's parameters file replaces whole top-level keys. If `conf/test/parameters.yml` sets only `model_options.test_size`, the other `model_options` keys from `base` are gone. Repeat the keys you need." | sc gives a concrete key example. |
| Removed APIs list | raw:L166-175: code block under "## Wrong APIs: do not generate these" showing `# WRONG: none of these exist`. Lists `context.run()`, `load_context`, `from kedro.runner import KedroSession`, `from kedro.io import KedroDataCatalog`, undefined fixtures. | sc:L173-184: table under "## Imports and APIs that do not exist in Kedro 1.x" with columns "Don't write / Write". sc lists both `from kedro.runner import KedroSession` and `from kedro.io import KedroSession`. | raw uses a code block with WRONG comments; sc uses a table mapping wrong to right. sc catches both import paths for KedroSession. |
| `conftest.py` example | raw:L177-198: full code block with `model_input_table` and `model_options` fixtures. | sc:L192: `conftest.py` appears in the layout tree; no fixture code shown. sc:L64 uses `model_input_table` and `model_options` fixtures it never defines. | Fixture code only in raw |
| `tests/` layout | raw:L200-207: plain path list (`src/...`, `tests/...`). | sc:L187-198: ASCII tree (`├──`, `└──`). | raw lists paths; sc draws a tree. |
| `pip install -e .` | raw:L209: "Install the project (`pip install -e .`) so tests can import it, and run `pytest` from the project root." | sc:L200: "The project has to be installed (`pip install -e .`) for tests to import it." | raw adds "and run `pytest` from the project root". |
| Coverage config | raw:L210-211: "Coverage comes from `pytest-cov` through `[tool.pytest.ini_options] addopts = "--cov src/<package>"` in `pyproject.toml`." | sc:L201-202: "For coverage, `pytest-cov` with `addopts = "--cov src/<package>"` under `[tool.pytest.ini_options]` in `pyproject.toml`." | Nearly identical. |

## Same fact, two styles

**Runner returns datasets**

raw:L75-86

> In Kedro 1.x, `runner.run(...)` returns `{output_name: dataset}` for the
> pipeline's outputs. Call `.load()` on the value, or use `catalog.load(name)`.
>
> ```python
> # WRONG: compares a MemoryDataset with a dict, always fails
> assert result["metrics"]["r2_score"] > 0
>
> # Correct
> assert result["metrics"].load()["r2_score"] > 0
> ```

sc:L83-88

> **The runner returns datasets, not data.** `runner.run()` returns
> `{output_name: dataset}` for the pipeline's outputs. Call `.load()` on each
> value (or use `catalog.load(name)`). Pre-1.0 runners returned the data itself,
> so older examples index straight into the result, as in
> `result["metrics"]["r2_score"]`. On 1.x that fails because the value is a
> `MemoryDataset`.

raw demonstrates the mistake in a labeled code block; sc explains the historical reason the mistake exists.

**Accuracy note (found while writing this record).** raw's `# WRONG` comment says indexing "compares a MemoryDataset with a dict, always fails". On Kedro 1.7.0 it actually raises `TypeError: 'MemoryDataset' object is not subscriptable` (checked 2026-10-13), which is what the round 1 no-skill run hit. The advice, call `.load()`, is right; the described failure is wrong. The snippet test did run the `# WRONG` line and asserted `TypeError`, so the behaviour was checked; nobody compared the comment's wording with what the test proved. Fixed in iteration 2. sc's version ("that fails because the value is a `MemoryDataset`") is accurate.

**Literal `params:` key**

raw:L95-100

> Register parameters under their **literal** input name:
>
> ```python
> # Correct
> catalog["params:model_options"] = {"test_size": 0.2, ...}
>
> # WRONG: the node asks for "params:model_options", so this is a missing input
> catalog["model_options"] = {"test_size": 0.2, ...}
> ```

sc:L94-96

> Parameters are registered under their literal input name. If a node
> declares `"params:model_options"`, the catalog key is `"params:model_options"`.
> Registering `"model_options"` leaves the input missing.

raw uses a Correct/Wrong comment pair; sc states the rule as an if-then proposition.

**Runtime params and env traps**

raw:L159-164

> - `runtime_params` must be **nested**. A dotted key like
>   `{"model_options.test_size": 0.5}` is not expanded. It becomes a literal key and
>   the real value is unchanged. (Only the CLI `--params` parses dots.)
> - A misspelled or missing `env` is **not** an error. Kedro silently uses base only.
> - A `parameters.yml` in the test env **replaces** whole top-level keys from
>   `base`. Repeat every sibling key you still need.

sc:L162-171

> Three traps:
>
> - **`runtime_params` must be nested.** Through the Python API, a dotted key
>   like `{"model_options.test_size": 0.5}` is stored as a literal key and the real
>   value is unchanged. Only the CLI's `--params` splits on dots.
> - **A missing env is silent.** `env="tset"` raises nothing and you get base
>   config, so a typo turns a test-config test into a production-config test.
> - **An env's parameters file replaces whole top-level keys.** If
>   `conf/test/parameters.yml` sets only `model_options.test_size`, the other
>   `model_options` keys from `base` are gone. Repeat the keys you need.

Both use bullets. sc adds a "Three traps" lead-in, bolds each rule, and gives concrete cases (`env="tset"`, the `model_options.test_size` file) with their consequence.

## Only in one version

Only in raw:

- Full `conftest.py` fixture code block with `model_input_table` and `model_options` (`raw:L177-198`).
- Explicit rule: "Never start a `KedroSession` to test a single node" (`raw:L23`).
- Note that "Outputs and intermediates do not need registering" (`raw:L102`).
- Inline code comment `# required, before KedroSession.create` (`raw:L136`).
- Run `pytest` from the project root (`raw:L209-210`).
- Point the catalog elsewhere through a test env if real writes matter (`raw:L144-145`).

Only in skill-creator:

- Explanation that `MemoryDataset` copies DataFrames and numpy arrays on load and save (`sc:L120-121`).
- Note that `session.run()` also returns `{name: dataset}` (`sc:L150`).
- "A test that asks for a fixture nobody defined fails at collection" (`sc:L22`).
- "Why each line looks like this" explanatory prose for the smoke test (`sc:L140-149`).
- Warning that the starter template uses `Path.cwd()` (`sc:L145-146`).
- Concrete example of env parameters file behavior (`sc:L169-171`).
- `from kedro.io import KedroSession` as a wrong import, and `kedro_context` as a nonexistent fixture (`sc:L19`, `sc:L181`).
- "Each layer up costs more and fails for more reasons" (`sc:L26`).
- Pre-1.0 runner behavior as context for `.load()` (`sc:L86-88`).

## How the differences showed up in evals

Round 1 (Sonnet agents, 5 tasks): both variants scored 25/25 checks with 5/5 first-try passes; the no-skill baseline scored 23/25 and 2/5.

Round 2 (with-skill only; baseline failed all 26):

| Test | raw gpt-4o | raw gpt-5.5 | sc gpt-4o | sc gpt-5.5 |
|---|---|---|---|---|
| Read run outputs with .load() | F | P | P | P |
| Register parameters under the literal params: key | F | P | F | P |
| Expose an intermediate instead of loading it after the run | F | P | F | P |
| Call bootstrap_project before creating a session | P | P | P | P |
| Nest runtime_params instead of using dotted keys | P | F | P | F |
| Replace load_context and context.run | P | F | F | F |
| Use pipeline_names instead of the deprecated pipeline_name | P | F | P | F |
| Define fixtures instead of assuming Kedro provides them | P | P | P | F |
| Unit-test a node without a session | P | F | P | F |
| A misspelled env is not an error ¹ | F | F | F | F |
| An env parameters file replaces whole top-level keys | F | P | F | F |
| MemoryDataset copies DataFrames between tests | F | F | F | F |
| Share fixtures through conftest.py | P | F | F | F |

¹ Not valid: the rubric expected the false claim that a misspelled env silently falls back to base config (`facts.md` 10b, corrected 2026-10-13). It failed in every cell, so it does not change the gap. Replaced by "Assert that the test env's values took effect".

Totals: raw 13/26, sc 10/26, baseline 0/26.

Cells where the two variants differed:

- Env parameters file on gpt-5.5: raw passed, sc failed. The sc answer wrote a test-env parameters file with only `test_size`, dropping `random_state` and `features`. A substance gap.
- Conftest on gpt-4o: raw passed, sc failed. The sc answer defined the fixtures in both files. Only raw shows a `conftest.py`, so this one was expected. A substance gap.
- Fixtures not provided on gpt-5.5: raw passed, sc failed. The sc code passed all code checks, but the rubric failed it for not explaining that Kedro provides no fixtures. A wording gap.
- load_context on gpt-4o: raw passed, sc failed. The sc code passed all code checks, but the rubric failed it for not saying that `load_context` and `context.run` no longer exist. A wording gap.
- .load() on gpt-4o: raw failed, sc passed. The raw answer indexed `result["metrics"]["r2_score"]` instead of calling `.load()`. A substance gap.

That gives raw 2 substance wins versus sc 1 substance win on code. MemoryDataset copying failed everywhere even though only sc covers it. These are one-run-per-cell scores; the 3-point gap is within noise, and the cause of raw's higher score is not established.

## Raw text diff

A unified diff is in [skills.diff](skills.diff) next to this file. The two files share almost no lines, so the tables above are the useful comparison.

Regenerate it with:

```bash
git diff --no-index skills/testing-pipelines-raw/SKILL.md skills/testing-pipelines-skill-creator/SKILL.md > docs/skill-creation-comparison/skills.diff
```