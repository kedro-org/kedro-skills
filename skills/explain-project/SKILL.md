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

**Use this skill when the user wants to understand a Kedro project as it is: an overview, a walkthrough of one pipeline, where a dataset comes from or goes, whether an output is saved, what a parameter controls, which versions or credentials it needs, or how to see it in Kedro-Viz. If the request is only to write, change, fix or test code, or to audit the project against best practices, stop here: this skill has nothing to add and must not be mentioned. In a mixed request, use it for the explanation part only.**

Answer in the conversation, and save an overview to a file only if the user asks. Flag concrete problems you find without fixing them. Apart from an overview file the user asks for, explaining is read-only: do not create, edit or delete project files, install packages without asking, or run the pipeline, call node functions or load datasets (Rule 7).

For the rules behind catalog entries, parameters or LLM context nodes, follow the `catalog-config`, `parameters-and-config` or `llm-context-nodes` skill if it is installed.

**CRITICAL:** Describe what Kedro resolves, not what file names or the order of code suggest. The pipeline registry decides which pipelines exist, dataset names decide the order nodes run in, and a dataset with no catalog entry or matching factory is kept in memory and never saved. A pipeline folder missing from the registry was skipped by discovery, usually after a failed import, unless the registry code leaves it out or renames it. Check the installed versions first, ask before loading the project's code, and never print credential values.

## Find the project

In `pyproject.toml`, `[tool.kedro]` gives `package_name` and `source_dir` (usually `src`); below, `src/<package>/` stands for that location. Its `tools` and `example_pipeline` keys only record `kedro new` options: a starter says `example_pipeline = "False"` and still ships pipelines. If the repository holds several Kedro projects, explain the one the request or working directory points to.

In `src/<package>/settings.py`, `CONF_SOURCE` can move the configuration folder, and `CONFIG_LOADER_ARGS` can rename the environments (`base_env`, `default_run_env`), change which files are read (`config_patterns`) or set how environments merge (`merge_strategy`). By default an environment replaces each top-level key it defines; `soft` merges nested keys instead. Runtime parameters (`--params`, `runtime_params`) are applied to the run environment before it merges with base: under the default merge, overriding `model.factor` replaces base's whole `model` group if that environment has a parameters file; with `soft`, or no file there, the other keys survive. The template sets `OmegaConfigLoader`, `base_env` and `default_run_env` itself, so only other values are customisations. Explain the environment the user names, otherwise the default run environment, and say which one you explained.

## Check the installed versions first

Run this first for every request, even a narrow one. It reads package metadata only, loads no project code and needs no consent. Its result decides whether the snapshot is available and which Kedro-Viz flags exist:

```bash
python -c "import sys, importlib.metadata as m; print(sys.executable); print({p: next((d.version for d in m.distributions(name=p)), None) for p in ('kedro', 'kedro-datasets', 'kedro-viz')})"
```

The first line shows which interpreter answered, and it may not be the project's. You are probably in the wrong environment if `kedro` is `None`, the path is not inside an environment (`/envs/`, `/.venv/`, `/virtualenvs/`), or the version does not meet the project's pin in `requirements.txt` or `pyproject.toml`. Then re-run it with the project's interpreter (a `.venv` in the project, `<env-path>/bin/python` or `conda run -n <env> python`), and ask if you cannot tell which that is. If none works, report the pin and say the installed version is unverified. Take every version in your answer from the same interpreter. Never infer what is installed from the user's words or a failed command: a user who cannot install the project's dependencies usually still has Kedro.

`kedro_init_version` in `pyproject.toml` (the snapshot's `metadata.kedro_version`) is the version the project was created with: report it beside the installed one and mention any gap.

- **1.6.0 or later**: the full snapshot below.
- **1.4.0 to 1.5.x**: snapshot nodes have no `func_name` or `source`; take function names and locations from the pipeline files.
- **Below 1.4.0**: there is no inspection API. Use `kedro registry list` and `kedro registry describe <name>`, then the files. They also load the project's code (step 1 below).

## Read the project

For a walkthrough, take a snapshot, check it against the files, then read the code. For a focused question, answer from the files with just what it needs: for a dataset, its producers back to the raw inputs, naming each one's catalog type and file path, then its storage and its consumers; for a parameter, where it is set, what overrides it and which nodes read it; for a pipeline, its registration, nodes, inputs and outputs.

**1. Ask before loading the project's code.** A snapshot imports the project's modules, builds its pipelines and loads its configuration. It runs no node and loads no data, but import-time code, a custom config loader or the logging setup can still have side effects. Ask before the first command that loads the project, unless the user already agreed in this conversation, for example by saying you may run commands that load the project's code. A request for an explanation is not agreement, and a tool's approval prompt is not enough, because some tools run commands without one. Work from the files meanwhile, and if the user says no, use "Without the snapshot".

**2. Take the snapshot once.** From the project root, with the project's interpreter:

```bash
python -c "import dataclasses, json; from kedro.inspection import get_project_snapshot; s = dataclasses.asdict(get_project_snapshot('.')); key = lambda n: (n['name'], str(n['inputs']), str(n['outputs'])); named = {key(n) for p in s['pipelines'] if p['name'] != '__default__' for n in p['nodes']}; [p.update(node_count=len(p['nodes']), nodes=[n for n in p['nodes'] if key(n) not in named]) for p in s['pipelines'] if p['name'] == '__default__']; print(json.dumps({k: s[k] for k in ('metadata', 'datasets', 'parameters', 'pipelines')}, indent=1))"
```

For `__default__`, which usually repeats the other pipelines, it prints the node count and only the nodes no other pipeline has. If the output is too long, remove `if p['name'] == '__default__'` for node counts only, then filter `s['pipelines']` by name to print one pipeline's nodes.

Pass `env='<name>'`, `conf_source='<path>'` (Kedro 1.5.0+) or `runtime_params={...}` (Kedro 1.6.0+, only with values the user gives you) to change the environment, configuration folder or run values. Reuse it until the code, configuration, interpreter, environment or runtime parameters change. The snapshot holds:

- `metadata`: project and package names, and `kedro_version`, which is `kedro_init_version`, not the installed version.
- `pipelines`: every registered pipeline with its free `inputs` and final `outputs`, and its nodes in a valid run order, each with `name`, `func_name`, `namespace`, `tags`, `inputs`, `outputs` and `source` (file and line range).
- `datasets`: catalog entries, plus pipeline datasets resolved through factory patterns, with `type` and `filepath` only. Read the catalog files for patterns, layers, versioning, `load_args` and `credentials` keys.
- `parameters`: top-level parameter keys, without values or the file that sets them. Find the file with `grep -rn '^<key>:'` in the configuration folder, skipping credentials files, before naming it.

It does not show what hooks change during a run or prove that the pipelines run.

**If `datasets` and `parameters` come back empty although the configuration folder has catalog and parameter files, the configuration did not load.** The usual cause is a missing run-environment folder (usually `conf/local/`): the template commits `conf/local/.gitkeep`, so a missing one is not a normal clone, and every command that loads the configuration, `kedro run` included, fails with `MissingConfigException` until it exists. An empty folder is fine. Check that folder, `CONF_SOURCE` and the environment name before naming the cause, suggest creating the folder only if it is missing, and explain from the YAML files meanwhile rather than report an empty catalog.

**3. Cross-check with the files.**

- `src/<package>/pipeline_registry.py`: how pipelines are registered and what `__default__` contains (Rule 1).
- `src/<package>/pipelines/*/`: every folder should appear in the registry (Rule 2).
- `src/<package>/settings.py`: uncommented settings only, mainly `HOOKS` and `DISABLE_HOOKS_FOR_PLUGINS` (Rule 8).
- The configuration folder: the environments, catalog and parameter files, and `globals.yml`.
- `pyproject.toml` or `requirements.txt`: the libraries in use.
- `tests/`, `notebooks/`, `README.md` and deployment files such as `Dockerfile` or `databricks.yml`: say what exists.

**4. Read the code.** Open each node function at its `source` location (or from the pipeline file when `source` is missing), with the helpers or SQL it relies on (logic often lives outside `nodes.py`), and describe what it does to the data in domain terms. Names, docstrings and the README are hints, not evidence. Tests show intended behaviour, but do not run them (Rule 7).

## Rules

### 1. The registry decides what exists and what runs

`register_pipelines()` in `pipeline_registry.py` returns the pipelines Kedro knows, under the names `kedro run --pipeline <name>` accepts. With `find_pipelines()`, each folder in `src/<package>/pipelines/` that exposes `create_pipeline()` becomes a pipeline named after the folder, and the template sets `__default__` to their sum, which is what a bare `kedro run` executes. A hand-written registry can rename, combine, filter or leave out pipelines, or make `__default__` a subset. Follow its code as far as it goes, and name anything you cannot resolve. Use the registry's names.

### 2. A pipeline folder missing from the registry usually failed to import

Projects created before Kedro 1.2.0 call `find_pipelines()` without `raise_errors=True`. When a pipeline's module fails to import, Kedro only logs a `UserWarning` ("An error occurred while importing the '<package>.pipelines.<name>' module") and leaves the pipeline out of the registry and out of `__default__`. It also skips, with a warning, a module that has no `create_pipeline()` or whose `create_pipeline()` does not return a `Pipeline`.

Compare the registry with the pipeline folders. Unless the registry code leaves a folder out or registers it under another name (Rule 1), report the cause the warning gives rather than calling it a missing pipeline, and say that the registered pipelines and `__default__` are incomplete. With `raise_errors=True`, the template default since 1.2.0, the same failure stops `kedro registry list` and the snapshot with an error instead; report it as shown.

### 3. Nodes connect by dataset name, not by their order in the file

A node's input comes from whichever node outputs a dataset of the same name; `params:<key>` and `parameters` inputs come from the parameters. Nodes on independent branches have no fixed order between them, and the order of `Node(...)` calls in `pipeline.py` means nothing. For dict inputs or outputs, read the dict to match function arguments or returned keys to datasets; the snapshot's lists lose that mapping.

A dataset produced by one pipeline and read by another links them. Such a pipeline runs on its own only if something provides the linking dataset: data already saved through its catalog entry or factory, or a hook. If nothing provides it, `kedro run --pipeline <name>` stops before any node runs with `ValueError: Pipeline input(s) {...} not found in the DataCatalog`. A `params:` input with no matching parameter fails the same way.

### 4. A dataset with no catalog entry is in memory and is not saved

Only names in the catalog, directly or through a factory pattern, are loaded from or saved to storage, unless their type is `MemoryDataset`; patterns match by specificity, not by their order in the file. Every other name is a `MemoryDataset` that is never saved: `kedro run` discards it, and `session.run()` returns only the final outputs to a Python caller. Keeping intermediates in memory is normal, but a final output or model that no catalog entry, factory or hook saves is worth flagging, as a question rather than a defect. To keep a dict such as `metrics`, a `json.JSONDataset` entry works; `tracking.MetricsDataset` and `tracking.JSONDataset` were removed in kedro-datasets 7.0.0, so never suggest them, and flag existing entries that use them: from 7.0.0, a pipeline that uses one fails with `DatasetError` before any node runs.

The snapshot leaves names with no catalog entry or matching factory out of `datasets`; an explicit `MemoryDataset` entry still appears. `kedro catalog describe-datasets` lists them under `defaults`, but it creates a session and runs hooks (step 1). Names that differ only after an `@` (`companies@pandas`) are one dataset loaded and saved through different types (transcoding). A catalog entry describes intended storage, not proof that the data exists.

### 5. Namespaces rename nodes, datasets and parameters

`Pipeline(..., namespace="candidate")` prefixes node names, datasets and parameters (`candidate.regressor`, `params:candidate.model_options`), except names mapped through `inputs=`, `outputs=` or `parameters=`, and except datasets and parameters when `prefix_datasets_with_namespace=False`. A catalog entry for `regressor` does not cover `candidate.regressor`: unless a factory pattern matches the prefixed name, the reused pipeline's model stays in memory. The `namespace=` argument on a single `Node` only labels the node; it does not rename its datasets. Explain a reused pipeline once, then for each instance give its node names and how function arguments and returned keys map to its datasets and parameters.

### 6. Never expose secrets

Do not read or quote `conf/local/credentials.yml`, any other credentials file, `.env` files or environment variable values, and never repeat a credential value, even a fake one or one quoted in a README, or a URL or connection string that contains a password or key. Refer to credentials by the key a catalog entry names (`credentials: dev_s3`) or by the environment variable's name. A fresh clone has an empty `conf/local/` and no credentials: report them as setup still to do, not as a defect. `${oc.env:VAR}` works in credentials files by default; other files need it registered as a custom resolver.

### 7. Do not run the pipeline or start a server to explain it

`kedro run` executes nodes: it overwrites data and can write to databases, cloud storage or paid APIs. Explaining never requires running the pipeline, calling node functions or loading datasets, and tests can run the pipeline too.

`kedro viz run` (or `kedro viz`, even with `--save-file`) and `kedro server start` start servers that do not return and would block your shell. Give the user the command instead. If asked to start Kedro-Viz, run it in the background if your tool can, and say so.

### 8. Hooks and plugins change behaviour outside the pipelines

Project hooks are listed in `HOOKS` in `settings.py`. Installed plugins register their hooks automatically unless named in `DISABLE_HOOKS_FOR_PLUGINS`, and `kedro info` shows which plugins have `hooks` entry points. A hook can add datasets to the catalog, replace a node's inputs before it runs (`before_node_run`) or send data to other services, so read each project hook and name each plugin hook. Kedro-Viz runs without hooks unless started with `--include-hooks` (Kedro-Viz 9.0.0+), so catalog changes made by hooks do not appear in it.

## Kedro-Viz

Give the user a command for the pipeline and environment you explained, leaving out flags that match the defaults:

```bash
kedro viz run --pipeline <name> --env <env>  # same as `kedro viz`; serves http://127.0.0.1:4141
kedro viz run --include-hooks                # Kedro-Viz 9.0.0+; runs the project's hooks
kedro viz run --lite                         # Kedro-Viz 10.0.0+; works without the project's dependencies
```

Offer only the flags the installed Kedro-Viz supports, not a list to try. Say what this project will show: its registered pipelines by name, and the nodes and datasets your explanation discussed. Mention namespace groups, layers or hook-added datasets only if the project has them. Describe it as what the user will see, not as something you viewed.

- `--lite` is experimental: it shows the pipeline structure without the project's dependencies, but not dataset types or layers, and lists what is missing.
- Layers come from `metadata: kedro-viz: layer:` in catalog entries.
- Kedro-Viz removed experiment tracking in 11.0.0; point users to `kedro-mlflow` instead, and flag a `SQLiteStore` session store in `settings.py` as a leftover.

## Structure the explanation

For a walkthrough, lead with what the project does and its main path from inputs to outputs, then cover these areas, skipping any that would be empty:

1. **Overview**: purpose, main inputs and outputs, the installed and creation Kedro versions, and the few files a newcomer should read first.
2. **Pipelines**: a table of the registered pipelines with what each consumes, produces and is for; which pipelines `kedro run` runs; reused pipelines and their namespaces.
3. **Data flow**: from raw inputs to final outputs across pipelines, as a short text flow (`raw inputs → pipeline → key dataset → final outputs`) or a small table. Stay at pipeline and key-dataset level, group repeated nodes, and leave the node-level graph to Kedro-Viz. Every arrow must be a real producer-to-consumer step: draw a node's sibling outputs as branches, not a chain.
4. **Data Catalog**: saved datasets by layer or `data/` folder with type and path, factory patterns, versioned datasets, credential keys by name, and what stays in memory, including split and intermediate outputs.
5. **Parameters and configuration**: parameter groups and the nodes that read them, the environments and which one you explained, and settings that differ from the template. Apply the merge rules under Find the project, and treat run-time values the user has not given as unknowns.
6. **Where the logic lives**: node functions as `file:line`, plus code outside nodes that changes results, such as helpers, SQL, hooks and custom datasets.
7. **Kedro features in use**: only those present, with where and how this project uses them, without teaching how to write them.
8. **Worth investigating**: concrete findings, each with its evidence and the next thing to check. For example: a final output or model that nothing saves, catalog entries no registered pipeline uses, pipeline folders that fail to import, parameters no node reads, nodes without `name=` and leftovers from removed features. No generic advice such as "add more tests"; configuration or access you cannot resolve is a limit of the explanation, not a defect.
9. **See it in Kedro-Viz**: the command, and what to look at first.

Back each statement about code or configuration with a file reference (`path:line` when you have one), and keep what the code shows apart from what you infer. Before saying a file or folder is missing or empty, list it with `ls -a <path>`: globs, `ls` of a parent folder and `git ls-files` miss `.gitkeep` files and git-ignored data. For a node without `name=`, use its function name, as Kedro-Viz does. Quote only the parts of the snapshot and catalog the answer needs, and skip standard template files (`__main__.py`, `settings.py` comments, `conf/logging.yml`, empty parameter files) unless they differ from the template.

**Before answering, check** every arrow against node inputs and outputs, every storage claim against catalog entries, factories, hooks and dataset types, every node output against the dataset that saves it, and every parameter value against the merge rules. Then say what the explanation is based on (files, a snapshot, or a Kedro-Viz graph you actually saw) and what you could not verify; claim test runs, data access or pipeline runs only if they happened.

## Without the snapshot

If the user declines, the snapshot is unavailable or fails, or you cannot run commands, explain from the files and say that the explanation was not checked against the installed code. Do not install packages or edit the project to make it load. When the project's dependencies are missing on this machine (the user says so, or loading fails with an `ImportError` for an uninstalled package), say plainly that loading fails here because of them, not because the project is broken, and name the missing packages if known.

- Read `pipeline_registry.py` and each pipeline definition, follow the registration as far as the code allows, and apply namespaces and `inputs=`, `outputs=` and `parameters=` mappings yourself (Rule 5).
- Combine the catalog and parameter files of the base environment with those of the run environment (`conf/base` and `conf/local` unless the settings say otherwise), with the merge rules under Find the project. A name with no entry and no matching factory pattern is in memory (Rule 4).
- For the graph, suggest `kedro viz run`, or `--lite` if the dependencies are missing.

## When unsure

- Inspection API, replacing `{version}` with the installed version or `stable`: `https://docs.kedro.org/en/{version}/inspect/inspect-project/`
