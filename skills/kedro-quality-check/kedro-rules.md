# Kedro ML Pipeline Review: Good Patterns and Anti-Patterns
 
> API-specific points are based on general Kedro knowledge. Check them against the project's pinned Kedro version.
 
## Kedro version and APIs
 
The project runs on the Kedro version it says it uses, with no outdated or made-up APIs.
 
**Good pattern**
 
- Version pinned in `pyproject.toml` and `requirements`.
- Only APIs that exist in that version (e.g. `OmegaConfigLoader`, `kedro_datasets`, `AbstractDataset`).
- Deprecation warnings treated as to-dos.
**Anti-pattern**
 
- Using removed or renamed APIs (`kedro.extras.datasets`, `TemplatedConfigLoader`, `AbstractDataSet`).
- Copying snippets from old blogs or LLM output without checking them against the pinned version.
## Data catalog
 
Every dataset in or out is declared once, so code has no paths and the data flow is visible.
 
**Good pattern**
 
- Every input and output declared once in `catalog.yml`.
- Nodes take and return objects only.
- Dataset factories and `globals` used to avoid repetition.
**Anti-pattern**
 
- Hard-coded paths or `pd.read_csv(...)` inside nodes.
- Calling `catalog.load()` inside a node.
- Intermediates saved ad hoc with `to_parquet`, so the pipeline graph hides them.
## Configuration and parameters
 
Behaviour can change without code changes, and each environment gets the right settings.
 
**Good pattern**
 
- Tunables live in `parameters.yml` and are passed as `params:xxx`.
- `conf/base` holds defaults, and `conf/local` or named envs (`dev`, `prod`) hold overrides.
- Environment-specific values come from `oc.env` or `globals`.
**Anti-pattern**
 
- Magic numbers, thresholds or column lists in code.
- Copy-pasted config per environment.
- Editing `base` to switch environments.
## Credentials, security and sensitive data
 
Nothing sensitive ends up in git, logs, test data or shared outputs, and nothing in config or data can run as code.
 
**Good pattern**
 
- Secrets in `conf/local/credentials.yml` (gitignored) or environment variables.
- Real data kept out of the repo and tests (synthetic fixtures instead).
- Safe loaders only.
- Sensitive columns masked in logs and outputs.
**Anti-pattern**
 
- Keys in `catalog.yml`, parameters or notebooks.
- `pickle` datasets from untrusted sources.
- `eval` or `yaml.load` on config or data.
- Printing dataframes with PII.
- Real extracts committed as test data.
## Node design
 
Each step is small, testable and easy to read, so it can be reused and debugged.
 
**Good pattern**
 
- Pure functions with a single job, typed signatures and docstrings.
- Explicit inputs and outputs, no side effects.
- Unit-tested with small fixtures.
**Anti-pattern**
 
- "God nodes" that load, clean, train and evaluate in one function.
- Reading globals or files, or mutating inputs in place.
- Nodes that can only be tested by running the whole pipeline.
## Pipeline design and modularity
 
The flow is clear, and parts can be reused, run on their own or deployed separately.
 
**Good pattern**
 
- Pipelines split by stage (ingest, features, train, evaluate).
- `pipeline()` with namespaces for reuse.
- Tags or `--from-nodes` / `--to-outputs` for partial runs.
- Pipelines registered by name.
**Anti-pattern**
 
- One monolithic pipeline.
- Copy-pasted pipelines instead of namespaces.
- Hidden dependencies between nodes through shared files.
- Stages that can't run alone.
## Data validation
 
Bad data is stopped early instead of failing deep in a run or quietly skewing results.
 
**Good pattern**
 
- Schema and quality checks at ingestion and before training (e.g. Pandera, Great Expectations).
- Parameters validated (e.g. Pydantic).
- Fails fast with a clear message.
**Anti-pattern**
 
- Trusting upstream data.
- Silent `fillna` or `dropna` that hides problems.
- Errors that only appear as a shape mismatch deep in training.
- Checks written but never enforced.
## Code style and linting
 
Code looks the same across the team, and simple mistakes are caught before review.
 
**Good pattern**
 
- One formatter and linter (e.g. Ruff) enforced via pre-commit and CI.
- Consistent naming and typing.
**Anti-pattern**
 
- Per-person style.
- Linting that only runs on request.
- Unused imports and dead nodes left in.
## Hooks and logging
 
You can see what happened in a run without changing node code.
 
**Good pattern**
 
- Hooks (`@hook_impl`) for cross-cutting needs: timing, data-shape logging, MLflow tracking, validation.
- The standard `logging` module with levels.
**Anti-pattern**
 
- `print` statements and ad hoc timers inside nodes.
- Logging secrets or raw data.
- Observability code mixed into business logic.
## Docs and visualisation
 
Others can understand the pipeline, run it and take it over.
 
**Good pattern**
 
- README with setup and run steps.
- Docstrings on nodes.
- Kedro-Viz kept current, with meaningful node and dataset names.
- Catalog entries documented.
**Anti-pattern**
 
- Out-of-date or missing README.
- Names like `node1` and `df_final2`.
- Knowledge only in one person's head.
 