---
name: explain-project
description: >-
  Guidance for explaining an existing Kedro project, covering its structure,
  registered pipelines, data flow, Data Catalog, parameters, configuration,
  credentials, hooks and Kedro-Viz. Use when asked to explain, summarise or
  review how a project is built, to onboard onto it, or to answer a question
  about it, such as where a dataset, parameter or piece of logic lives, whether
  an output is saved, which Kedro version it uses, which credentials it needs,
  or how to view it or its experiment tracking in Kedro-Viz. Adds nothing when
  writing or changing code, or for a full best-practice audit.
---
# Explain an existing Kedro project

## Scope

**Use this skill when the user wants to understand a Kedro project as it is: an overview, a walkthrough of one pipeline, where a dataset comes from or goes, whether an output is saved, what a parameter controls, which versions or credentials it needs, or how to see it in Kedro-Viz. If the request is to write, change, fix or test code, or to audit the project against best practices, stop here: this skill has nothing to add and must not be mentioned.**

Answer in the conversation; save an overview to a file only if the user asks. Flag concrete problems you find, but do not change code to fix them. Explaining is read-only: do not create, edit or delete project files, install packages without asking, or run the pipeline, call node functions or load datasets (Rule 8).

For the rules behind catalog entries, parameters or LLM context nodes, follow the `catalog-config`, `parameters-and-config` or `llm-context-nodes` skill if it is installed.

**CRITICAL:** Describe what Kedro resolves, not what file names or the order of code suggest. The pipeline registry decides which pipelines exist, dataset names decide the order nodes run in, and a dataset with no catalog entry is kept in memory and never saved. A pipeline folder missing from the registry failed to import unless the registry code leaves it out or renames it. Ask before loading the project's code, and never print credential values.

## Find the project

In `pyproject.toml`, `[tool.kedro]` gives `package_name` and `source_dir` (usually `src`); below, `src/<package>/` stands for that location. Its `tools` and `example_pipeline` keys only record the options `kedro new` ran with: a starter project says `example_pipeline = "False"` and still ships its pipelines. If the repository holds several Kedro projects, explain the one the request or working directory points to.

In `src/<package>/settings.py`, `CONF_SOURCE` can move the configuration folder, and `CONFIG_LOADER_ARGS` can rename the environments (`base_env`, `default_run_env`) or change which files are read (`config_patterns`). The template itself sets `CONFIG_LOADER_CLASS = OmegaConfigLoader` and `CONFIG_LOADER_ARGS` with `base_env` and `default_run_env`, so only other values are customisations. Explain the environment the user names, otherwise the default run environment, and say which one you explained.

## Check the installed versions first

Run this first for every request, even a narrow one. It reads package metadata only, loads no project code and needs no consent. Its result decides whether the snapshot is available and which Kedro-Viz flags exist:

```bash
python -c "import sys, importlib.metadata as m; print(sys.executable); print({p: next((d.version for d in m.distributions(name=p)), None) for p in ('kedro', 'kedro-datasets', 'kedro-viz')})"
```

`None` means not installed in that interpreter, which may not be the user's environment: if `kedro` is `None` or the path is not inside an environment (`/envs/`, `/.venv/`, `/virtualenvs/`), re-run it with the project's interpreter (`<env-path>/bin/python` or `conda run -n <env> python`), and ask if you cannot tell which that is. If no interpreter works, fall back to the `kedro` pin in `requirements.txt` or `pyproject.toml` and say the installed version is unverified. Never infer what is installed from the user's words or a failed command: a user who cannot install the project's dependencies usually still has Kedro.

- **1.6.0 or later**: the full snapshot below.
- **1.4.0 to 1.5.x**: snapshot nodes have no `func_name` or `source`; take function names and locations from the pipeline files.
- **Below 1.4.0**: there is no inspection API. Use `kedro registry list` and `kedro registry describe <name>`, then the files. They also load the project's code (step 1 below).

## Read the project

For a walkthrough, take a snapshot, check it against the files, then read the code. For a question about one dataset, pipeline or parameter, trace just that chain from the files: back to its raw inputs with their catalog type and path, and on to its consumers. Leave out project-wide context the question does not need.

**1. Ask before loading the project's code.** A snapshot imports the project's modules, builds its pipelines and loads its configuration. It runs no node and loads no data, but import-time code, a custom config loader or the logging setup can still have side effects (the template's logging writes `info.log`). Ask before the first command that loads the project, unless the user already agreed in this conversation. A request for an explanation is not agreement, and a tool's approval prompt is not enough, because some tools run commands without one. Work from the files meanwhile, and if the user says no, use "Without the snapshot".

**2. Take the snapshot once.** From the project root, with the project's interpreter:

```bash
python -c "import dataclasses, json; from kedro.inspection import get_project_snapshot; s = dataclasses.asdict(get_project_snapshot('.')); key = lambda n: (n['name'], str(n['inputs']), str(n['outputs'])); named = {key(n) for p in s['pipelines'] if p['name'] != '__default__' for n in p['nodes']}; [p.update(node_count=len(p['nodes']), nodes=[n for n in p['nodes'] if key(n) not in named]) for p in s['pipelines'] if p['name'] == '__default__']; print(json.dumps({k: s[k] for k in ('metadata', 'datasets', 'parameters', 'pipelines')}, indent=1))"
```

For `__default__`, which usually repeats the other pipelines, it prints the node count and only the nodes no other pipeline has. It puts `pipelines` last so a cut-off output still shows the configuration. If the output is too long for your tool, remove `if p['name'] == '__default__'` to get node counts only, then print one pipeline's nodes at a time by filtering `s['pipelines']` on its name in the same command.

Pass `env='<name>'`, `conf_source='<path>'` (Kedro 1.5.0+) or `runtime_params={...}` (Kedro 1.6.0+, only with values the user gives you) to change the environment, configuration folder or run values. Reuse the result unless the code or configuration changes. The snapshot holds:

- `metadata`: project and package names, and `kedro_version`, which is `kedro_init_version` from `pyproject.toml` (Rule 6).
- `pipelines`: every registered pipeline with its free `inputs` and final `outputs`, and its nodes in a valid run order, each with `name`, `func_name`, `namespace`, `tags`, `inputs`, `outputs` and `source` (file and line range). `source` is missing for lambdas, `functools.partial` and functions outside the project.
- `datasets`: catalog entries, plus pipeline datasets resolved through factory patterns, with `type` and `filepath` only. Read the catalog files for the patterns themselves, layers, versioning, `load_args` and `credentials` keys.
- `parameters`: top-level parameter keys, without values or the file that sets them. Find the file with `grep -rn '^<key>:' conf/` before naming it.

It does not show what hooks change during a run or prove that the pipelines run.

**If `datasets` and `parameters` come back empty although the configuration folder has catalog and parameter files, the configuration did not load: the run environment's folder (usually `conf/local/`) is missing.** An empty folder is fine. The template commits `conf/local/.gitkeep`, so a missing folder is not a normal clone: `kedro run` and every command that loads the configuration fail with `MissingConfigException` until it exists. Tell the user that creating the empty folder fixes it, read the YAML files meanwhile, and do not report an empty catalog.

**3. Cross-check with the files.**

- `src/<package>/pipeline_registry.py`: how pipelines are registered and what `__default__` contains (Rule 1).
- `src/<package>/pipelines/*/`: every folder should appear in the registry (Rule 2).
- `src/<package>/settings.py`: uncommented settings only, mainly `HOOKS` and `DISABLE_HOOKS_FOR_PLUGINS` (Rule 9).
- The configuration folder: the environments, catalog and parameter files, and `globals.yml`.
- `pyproject.toml` or `requirements.txt`: the libraries in use.
- `tests/`, `notebooks/`, `README.md` and deployment files such as `Dockerfile` or `databricks.yml`: say what exists, without testing or deployment advice.

**4. Read the code.** Open each node function at its `source` location, with the helpers or SQL it relies on (logic often lives outside `nodes.py`), and describe what it does to the data in domain terms. Names, docstrings and the README are hints, not evidence. Tests show intended behaviour, but do not run them (Rule 8).

## Rules

### 1. The registry decides what exists and what runs

`register_pipelines()` in `pipeline_registry.py` returns the pipelines Kedro knows, under the names `kedro run --pipeline <name>` accepts. With `find_pipelines()`, each folder in `src/<package>/pipelines/` that exposes `create_pipeline()` becomes a pipeline named after the folder, and the template sets `__default__` to their sum, which is what a bare `kedro run` executes. A hand-written registry can rename, combine, filter or leave out pipelines, or make `__default__` a subset. Follow its code as far as it goes, and name anything you cannot resolve. Use the registry's names, and in a walkthrough say which pipelines `kedro run` runs.

### 2. A pipeline folder missing from the registry usually failed to import

Projects created before Kedro 1.2.0 call `find_pipelines()` without `raise_errors=True`. When a pipeline's module fails to import, usually because a dependency is not installed, Kedro only logs a `UserWarning` ("An error occurred while importing the '<package>.pipelines.<name>' module") and leaves the pipeline out of the registry and out of `__default__`.

Compare the registry with the pipeline folders. Unless the registry code leaves a folder out or registers it under another name (Rule 1), report it as an import failure with the cause from the warning, never as a pipeline that does not exist, and say that the registered pipelines and `__default__` are incomplete. With `raise_errors=True`, the template default since 1.2.0, the same failure stops `kedro registry list` and the snapshot with `ImportError`.

### 3. Nodes connect by dataset name, not by their order in the file

A node's input comes from whichever node outputs a dataset of the same name; `params:<key>` and `parameters` inputs come from the parameters. The snapshot lists nodes in an order Kedro can run them in. Nodes on independent branches have no fixed order between them, and the order of `Node(...)` calls in `pipeline.py` means nothing. For dict inputs or outputs, read the dict to match function arguments or returned keys to datasets; the snapshot's lists lose that mapping.

A dataset produced by one pipeline and read by another links them: in the starter, `reporting` reads `preprocessed_shuttles` from `data_processing`. Such a pipeline runs on its own only if the linking dataset is in the catalog and an earlier run saved it. If it has no catalog entry, `kedro run --pipeline <name>` stops before any node runs with `ValueError: Pipeline input(s) {...} not found in the DataCatalog`. A `params:` input with no matching parameter fails the same way.

### 4. A dataset with no catalog entry is in memory and is not saved

Only names in the catalog, directly or through a factory pattern, are loaded from or saved to storage; patterns match by specificity, not by their order in the file. Every other name is a `MemoryDataset` that is never saved: `kedro run` discards it, and `session.run()` returns only the final outputs to a Python caller. Keeping intermediates in memory is normal, but a final output or model that no catalog entry, factory or hook saves is worth flagging, as a question rather than a defect: in the starter, `kedro run` computes `metrics` and discards it, and only the R² score reaches the log. To keep a dict such as `metrics`, a `json.JSONDataset` entry works; `tracking.MetricsDataset` and `tracking.JSONDataset` were removed in kedro-datasets 7.0.0, so never suggest them, and flag existing entries that use them: from 7.0.0, a pipeline that uses one fails with `DatasetError` before any node runs.

The snapshot leaves in-memory names out of `datasets`. `kedro catalog describe-datasets` lists them under `defaults`, but it creates a session and runs hooks (step 1). Names that differ only after an `@` (`companies@pandas`) are one dataset loaded and saved through different types (transcoding). A catalog entry describes intended storage, not proof that the data exists.

### 5. Namespaces rename nodes, datasets and parameters

`Pipeline(..., namespace="candidate")` prefixes node names, datasets and parameters (`candidate.regressor`, `params:candidate.model_options`), except names mapped through `inputs=`, `outputs=` or `parameters=`, and except datasets and parameters when `prefix_datasets_with_namespace=False`. A catalog entry for `regressor` does not cover `candidate.regressor`: unless a factory pattern matches the prefixed name, the reused pipeline's model stays in memory. The `namespace=` argument on a single `Node` only labels the node; it does not rename its datasets. Explain a reused pipeline once, then for each instance give its node names and how function arguments and returned keys map to its datasets and parameters.

### 6. `kedro_init_version` is not the installed version

`kedro_init_version` in `pyproject.toml`, which the snapshot reports as `metadata.kedro_version`, is the Kedro version the project was created with. Report the installed version from the check above, and mention any gap: an older template may lack `raise_errors=True` or the inspection API.

### 7. Never expose secrets

Do not read or quote `conf/local/credentials.yml`, any other credentials file, `.env` files or environment variable values, and never repeat a URL or connection string that contains a password or key. Refer to credentials by the key a catalog entry names (`credentials: dev_s3`) or by the environment variable's name. The template commits only `conf/local/.gitkeep`, so a fresh clone has an empty `conf/local/` and no credentials: report them as setup still to do, not as a defect. `${oc.env:VAR}` works in credentials files by default; other files need it registered as a custom resolver.

### 8. Do not run the pipeline or start a server to explain it

`kedro run` executes nodes: it overwrites data and can write to databases, cloud storage or paid APIs. Explaining a project never requires running the pipeline, calling node functions or loading datasets, and running the tests can run the pipeline too (the starter's `tests/test_run.py` calls `session.run()`).

`kedro viz run` (or `kedro viz`) and `kedro server start` start servers that do not return, so they would block your shell, and `kedro viz run --save-file` starts the server after saving. Give the user the command instead. If they ask you to start Kedro-Viz, run it in the background if your tool can, and tell them. `kedro viz build` (Kedro-Viz 7.1.0+) writes a static copy to `build/` and returns.

### 9. Hooks and plugins change behaviour outside the pipelines

Project hooks are listed in `HOOKS` in `settings.py`. Installed plugins register their hooks automatically unless named in `DISABLE_HOOKS_FOR_PLUGINS`, and `kedro info` shows which plugins have `hooks` entry points. A hook can add datasets to the catalog, replace a node's inputs before it runs (`before_node_run`) or send data to other services, so read each project hook and name each plugin hook. Kedro-Viz runs without hooks unless started with `--include-hooks` (Kedro-Viz 9.0.0+), so catalog changes made by hooks do not appear in it.

## Kedro-Viz

Give the user a command for the pipeline and environment you explained, leaving out flags that match the defaults:

```bash
kedro viz run --pipeline <name> --env <env>  # same as `kedro viz`; serves http://127.0.0.1:4141
kedro viz run --include-hooks                # Kedro-Viz 9.0.0+; runs the project's hooks
kedro viz run --lite                         # Kedro-Viz 10.0.0+; works without the project's dependencies
```

Offer only the flags the installed Kedro-Viz supports, not a list to try. Say what this project will show: its registered pipelines by name, and the nodes and datasets your explanation discussed. Mention namespace groups, layers or hook-added datasets only if the project has them. Do not describe the graph as if you had seen it.

- `--lite` is experimental: its graph is right, but not its dataset types or layers. It lists the missing dependencies.
- Layers come from `metadata: kedro-viz: layer:` in catalog entries.
- Kedro-Viz removed experiment tracking in 11.0.0. Do not send the user to it. A `SQLiteStore` session store in `settings.py` is a leftover worth flagging, as are `tracking.*` datasets (Rule 4); `kedro-mlflow` is the replacement.

## Structure the explanation

For a walkthrough, lead with what the project does and its main path from inputs to outputs, then cover these areas, skipping any that would be empty:

1. **Overview**: purpose, main inputs and outputs, the installed Kedro version (and the one it was created with, if different), and the few files a newcomer should read first.
2. **Pipelines**: a table of the registered pipelines with what each consumes, produces and is for; which pipelines `kedro run` runs; reused pipelines and their namespaces.
3. **Data flow**: from raw inputs to final outputs across pipelines, as a short text flow (`raw inputs → pipeline → key dataset → final outputs`) or a small table. Stay at pipeline and key-dataset level, group repeated nodes, and leave the node-level graph to Kedro-Viz.
4. **Data Catalog**: saved datasets by layer or `data/` folder with type and path, factory patterns, versioned datasets, credential keys by name, and what stays in memory, including split and intermediate outputs.
5. **Parameters and configuration**: parameter groups and the nodes that read them, the environments and which one you explained, and settings that differ from the template. Read the merge strategy before describing overrides, and leave values set at run time as unknowns.
6. **Where the logic lives**: node functions as `file:line`, plus code outside nodes that changes results, such as helpers, SQL, hooks and custom datasets.
7. **Kedro features in use**: only those present, with where and how this project uses them, without teaching how to write them.
8. **Worth investigating**: concrete findings, each with its evidence and the next thing to check. For example: a final output or model that nothing saves, catalog entries no registered pipeline uses, pipeline folders that fail to import, parameters no node reads, nodes without `name=` (their generated `<function>__<hash>` names change when their inputs or outputs do) and leftovers from removed features. No generic advice such as "add more tests"; configuration or access you cannot resolve is a limit of the explanation, not a defect.
9. **See it in Kedro-Viz**: the command, and what to look at first.

Back each statement about code or configuration with a file reference (`path:line` when you have one), and keep what the code shows apart from what you infer. Before saying a file or folder is missing or empty, list it with `ls -a <path>`: globs, `ls` of a parent folder and `git ls-files` miss `.gitkeep` files and git-ignored data. Use Kedro's names for pipelines, nodes and datasets; for a node without `name=`, use its function name, as Kedro-Viz does. Do not dump the snapshot or the whole catalog, or walk through standard template files (`__main__.py`, `settings.py` comments, `conf/logging.yml`, empty parameter files) unless they differ from the template. End by saying what the explanation is based on (files, a snapshot, or a Kedro-Viz graph you actually saw); claim test runs, data access or pipeline runs only if they happened.

## Without the snapshot

If the user declines, the snapshot is unavailable or fails, or you cannot run commands, explain from the files and say that the explanation was not checked against the installed code. Do not install packages or change the project to make the snapshot work unless the user asks. When the project's dependencies are missing on this machine (the user says so, or loading the project fails with `ImportError`), say plainly that loading the project fails here because of them, not because the project is broken, and name the missing packages if you know them.

- Read `pipeline_registry.py` and each pipeline definition, follow the registration as far as the code allows, and apply namespaces and `inputs=`, `outputs=` and `parameters=` mappings yourself (Rule 5).
- Combine the catalog and parameter files of the base environment with those of the run environment (`conf/base` and `conf/local` unless the settings say otherwise). A name with no entry and no matching factory pattern is in memory (Rule 4).
- For the graph, suggest `kedro viz run --lite` (Kedro-Viz 10.0.0+).

## When unsure

- Inspection API, replacing `{version}` with the installed version or `stable`: `https://docs.kedro.org/en/{version}/inspect/inspect-project/`
- Pipeline registry and `find_pipelines`: https://docs.kedro.org/en/stable/build/pipeline_registry/
- Configuration and environments: https://docs.kedro.org/en/stable/configure/configuration_basics/
- Kedro-Viz: https://docs.kedro.org/projects/kedro-viz/en/stable/
