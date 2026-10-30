---
name: kedro-deploy-databricks
description: >-
  Kedro deployment guidance for Databricks. Use when choosing between Git
  folders, Databricks Connect and Declarative Automation Bundles (DABs, formerly
  Databricks Asset Bundles), packaging a Kedro project as a wheel, generating or
  editing a bundle with kedro-databricks, getting conf and environments onto
  Databricks, using Unity Catalog volumes, reading secrets from secret scopes,
  mapping nodes to job tasks, or validating a bundle before deploying. Defers
  cluster configuration, permissions and Terraform or deploy-engine errors to
  Databricks documentation.
---
# Deploying a Kedro project to Databricks

## Scope

This skill covers the Kedro side of a Databricks deployment. Split every answer along these lines:

| Owner | Responsible for |
|-------|-----------------|
| Kedro | Pipelines, node grouping, the catalog, `conf/` and environments, packaging |
| kedro-databricks | Generating bundle YAML from the project: `databricks.yml`, `resources/*.yml`, `conf/<env>/databricks.yml` |
| Databricks | Compute and cluster configuration, permissions and grants, Unity Catalog setup, secret scopes, authentication, networking, deploy-engine errors |

kedro-databricks is a community-maintained plugin (`https://github.com/JenspederM/kedro-databricks`), not part of Kedro: check its version and open issues before relying on a behaviour. For anything in the Databricks row, say where the setting lives in the project and link the Databricks documentation listed under [Out of scope](#out-of-scope-defer-to-databricks). Never invent values such as `node_type_id`, `spark_version` or policy IDs.

**CRITICAL:** Never take kedro-databricks flags, bundle fields or Databricks behaviour from training data. Both change often. The installed code and `--help` output win over the docs, memory and this file, and versioned docs win over memory. Where kedro-databricks' docs disagree with its code, follow the code. Never generate these outdated patterns: `dbx`, `databricks configure --token`, `/dbfs/FileStore/...`, `dbfs:/mnt/...` or `/dbfs/mnt/...` paths, the `databricks-iris` starter, or a `conf/<env>/databricks.yml` with a top-level `default:` key instead of `resources:`.

## Step 1: check what is installed

Run this with the project's interpreter:

```bash
python - <<'EOF'
import sys
from importlib.metadata import PackageNotFoundError, version
print(sys.executable, "venv" if sys.prefix != sys.base_prefix else "")
for name in ("kedro", "kedro-databricks", "kedro-datasets"):
    try:
        print(name, version(name))
    except PackageNotFoundError:
        print(name, "not installed")
try:
    from kedro.inspection import validate_deployment_grouping  # noqa: F401
    print("grouping check: available")
except ImportError:
    print("grouping check: not available")
EOF
```

Your shell may not use the environment the user has activated. Trust the versions only if the first line ends in `venv` (a virtual environment) or the path contains `/envs/` (a conda environment). Otherwise re-run with the project's interpreter directly (`<env-path>/bin/python` or `conda run -n <env> python`). If you cannot tell which environment is the project's, ask. If no interpreter works, fall back to the `kedro` and `kedro-databricks` pins in `requirements.txt` or `pyproject.toml`, and say the versions are unverified.

Then read the tools' own help, and use only flags that appear in it:

```bash
databricks --version
kedro databricks --help
kedro databricks bundle --help
databricks bundle validate --help
```

- This skill assumes a Kedro release with `validate_deployment_grouping` and groups in the project snapshot (1.8.0 or later). Trust the `grouping check` line above, not the version number: development builds can report an older version and still have the check. If it says `not available`, say the check needs a newer Kedro, suggest upgrading, and do not invent the functions. Projects created with `kedro new` pin `kedro~=X.Y.Z` (or `kedro[jupyter]~=X.Y.Z`) in both `pyproject.toml` and `requirements.txt`, so change the pin in both files.
- `kedro databricks` is a project plugin: it only works inside a Kedro project, and it needs the Databricks CLI on `PATH`.
- If you cannot run commands, say so and flag every plugin or CLI detail in your answer as unverified.

## Step 2: read the current docs

Replace `{version}` with the installed version, or use `stable` / `latest`:

- Kedro on Databricks: `https://docs.kedro.org/en/{version}/deploy/supported-platforms/databricks/`
- Grouping nodes and checking a grouping: `https://docs.kedro.org/en/{version}/deploy/nodes_grouping/`
- kedro-databricks: `https://kedro-databricks.readthedocs.io/en/v{version}/` (note the `v`), and its changelog at `https://kedro-databricks.readthedocs.io/en/v{version}/changelog/`
- Databricks: start from the index at `https://docs.databricks.com/llms.txt`

If you have no web access, say which page you would have checked instead of answering from memory.

## Choose a path

| Path | Use it for | Notes |
|------|------------|-------|
| Git folders and a notebook | Interactive development in the workspace | Clone the repo into a Git folder, then `%load_ext kedro.ipython` and `%reload_kedro` in a notebook. Kedro's docs schedule this path as a job that runs the notebook. Databricks recommends bundles for CI/CD, and a Git folder that production jobs run from should be updated only by automation. |
| Databricks Connect | Running the pipeline locally against Databricks compute | `databricks-connect` and `pyspark` cannot be installed in the same environment. Pin `databricks-connect` to the compute's version. |
| Declarative Automation Bundles (DABs, formerly Databricks Asset Bundles) | Scheduled and production jobs | The project is built as a wheel and each task runs it. This is the path kedro-databricks targets. |

With Databricks Connect, check how the installed kedro-datasets decides to use it. In kedro-datasets 9.6.0, `SparkDatasetV2` only uses Databricks Connect when both `DATABRICKS_HOST` and `DATABRICKS_TOKEN` are set, and always asks for serverless compute; otherwise it quietly falls back to a local Spark session.

"Our own bundle with the wheel, or the plugin?" is not an either-or: kedro-databricks generates ordinary bundle YAML (`databricks.yml` plus `resources/*.yml`) with `python_wheel_task` tasks. Use the plugin to keep the job definitions in step with the pipelines. Hand-write the bundle when the plugin's generators do not fit. A hand-written bundle then has to do what the plugin did: build the wheel with `kedro package`, put `conf/` without `conf/local` where `--conf-source` points (synced workspace files, or `conf-<package_name>.tar.gz` on a volume), and upload input data to the volume.

## Packaging

- The wheel holds code only, never configuration. `kedro package` builds the wheel and a separate `conf-<package_name>.tar.gz`. The archive leaves out only the `.yml` files in `conf/local`: the folder and any `.yaml` or `.json` files in it are still packed, so never keep secrets in `conf/local/*.yaml` or `*.json`.
- With kedro-databricks, `databricks bundle deploy` builds the wheel by running `kedro package`, so Kedro and the project must be installed wherever the deploy runs, CI included.
- Each task runs the project's console script, which calls `kedro run` with the task's parameters. kedro-databricks 0.18.x takes the task's `entry_point` from `project_name`, not from `[project.scripts]`; they differ for names with underscores or digits, so check the generated YAML.
- Everything in `[project].dependencies` is installed into each job environment:
  - Keep `pyspark` out, because Databricks provides Spark. Use the kedro-datasets extras `spark-sparkdataset`, `spark-core` or `spark-databricks`, not `spark`, `spark-local`, `spark-all` or `spark-deltatabledataset`, which install `pyspark`. Install `pyspark` only in the local environment.
  - Development-only dependencies such as `jupyterlab`, `notebook` and `kedro-viz` slow down every task's start-up, and kedro-viz's hooks log warnings in every task; suggest moving them to an optional extra.
- On serverless jobs, each run installs the job environment again, so a redeployed wheel is picked up by the next run even with the same version number. If a job on other compute keeps running old code, bump the project version so the new wheel is installed.

## Configuration and environments

- A Kedro run with no `--env` uses `local`, and a missing `conf/local` raises `MissingConfigException`. `conf/local` is gitignored (except its `.gitkeep`) and excluded from kedro-databricks' sync, so it does not reach Databricks. Every task must pass `--env <env>`, and nothing a job needs can live in `conf/local`.
- `--conf-source` accepts a directory, a `.tar.gz` or `.zip`, or a remote URL. On Databricks use absolute paths (`/Workspace/...` or `/Volumes/...`).
- kedro-databricks syncs `conf/` to the bundle's workspace files and gives each task `--conf-source /${workspace.file_path}/conf --env ${var.environment}`. The generated `databricks.yml` sets `var.environment` and force-includes the gitignored conf folder only for its `dev` and `prod` targets, so a new target needs both.
- `kedro databricks init` needs an authenticated Databricks CLI. It writes `databricks.yml`, `conf/<target>/databricks.yml` (job overrides under a root `resources:` key) and `conf/<target>/catalog.yml`, but no jobs: `kedro databricks bundle` still has to run. `databricks.yml` contains the workspace host and, unless `init` ran as a service principal, the email of the user who ran `init` as the `prod` target's `run_as` (and in a comment above it). Review it before committing to a public repository, and change `run_as` if someone else or CI deploys `prod`. `init --overwrite` rewrites `conf/<target>/databricks.yml` and `conf/<target>/catalog.yml`, discarding your edits.
- That `conf/<target>/catalog.yml` is a copy of `conf/base/catalog.yml` only, with unquoted `data/...` file paths moved onto the volume (quoted paths are left as they are). Each copied entry replaces the base entry in that environment. Datasets in other catalog files and datasets added to `conf/base` later still load there but keep their local paths, and later edits to copied entries are hidden by the copy, so mirror them in `conf/<target>/catalog.yml` with volume paths.
- `init` adds `.databricks` and `conf/dev/**` (keeping `conf/dev/.gitkeep`) to `.gitignore`, so a clean CI checkout has an empty `conf/dev` and `kedro databricks bundle -e dev` fails there. Deploy a committed target such as `prod` from CI. Do not just remove the ignore: `conf/dev/catalog.yml` hardcodes the `init` user's name in `_file_path`, while the dev volume is named after whoever deploys.
- The `-e/--env` help text says "Defaults to `local`", but the plugin's real default is `default_env` in the `[tool.kedro-databricks]` table that `init` adds to `pyproject.toml` (`dev`). Always pass `-e <env>` explicitly.
- Kedro's config loader interpolates `${...}`. In Kedro-loaded files (`conf/<env>/databricks*.yml` and files under `conf/<env>/databricks/`), write bundle substitutions escaped, as `\${workspace.file_path}`, unquoted or in single quotes (inside double quotes write `"\\${workspace.file_path}"`). Do not escape them in `databricks.yml` or `resources/*.yml`, which Databricks reads directly. Keep all `resources:` overrides for one environment in one file, because Kedro rejects the same top-level key in two files.
- `resources/target.<env>.*.yml` files are generated. Do not hand-edit them: change `conf/<env>/databricks.yml` and regenerate with `kedro databricks bundle --overwrite`.
- If the project has a Spark hook or `spark.yml` that sets driver or executor options, it must not run on Databricks; serverless compute only accepts some Spark properties (link `https://docs.databricks.com/aws/en/spark/conf#serverless` for the list). When `src/<package>/hooks.py` has a `SparkHooks` class, `kedro databricks init` rewrites that file, dropping its comments, so that `SparkHooks.after_context_created` returns early unless the env is `local`; check the guard is there, and add it by hand if the hook has another name. Projects without a Spark hook, such as the current PySpark starter, need nothing here.

## Storage

- Use Unity Catalog volumes: `/Volumes/<catalog>/<schema>/<volume>/...` (Spark also accepts `dbfs:/Volumes/...`). Never use DBFS root, `/dbfs/FileStore`, mounts or `/dbfs/mnt`: they are deprecated, mounts do not work with serverless compute and DBFS access there is limited, and on Databricks Free Edition the public DBFS root is disabled.
- `kedro databricks init` adds a managed volume to `conf/<target>/databricks.yml`, in `workspace.default`, with read and write grants for the deploying user, and deploying creates it. Free Edition has `workspace.default`; other workspaces may not, so find the real catalog and schema (`databricks catalogs list`, `databricks schemas list <catalog>`) instead of assuming them.
- In kedro-databricks 0.18.3, `init --catalog <c> --schema <s>` moves the catalog's paths to `/Volumes/<c>/<s>/...` but leaves the volume in `workspace.default`. Set the volume's `catalog_name` and `schema_name` in `conf/<target>/databricks.yml` to match, then run `kedro databricks bundle -e <target> --overwrite`.
- Every dataset passed from one task to another must be on a volume or in a table. Local disk is not shared between tasks and is not guaranteed to survive from one task to the next.
- Workspace files (`/Workspace/...`) are for code and small files only (500 MB per file), and Spark executors cannot write to them.
- Apart from the volume `init` creates, grants on catalogs, schemas and volumes belong to Databricks.

## Secrets

- Neither Kedro nor kedro-databricks has a built-in resolver for Databricks secret scopes. Never put secret values in YAML, bundle variables or job parameters.
- For Databricks environments, credentials live in `conf/<env>/credentials.yml` as references only. This overrides the "credentials only in `conf/local`" rule in the `catalog-config` and `parameters-and-config` skills for those environments, because `conf/local` is never deployed.
- Two patterns work:
  1. Reference an environment variable in `conf/<env>/credentials.yml`, `password: ${oc.env:DB_PASSWORD}`, and have the job set it from a secret scope. On serverless jobs (environment version 5 or later), add a job-level `environment_variables` entry whose value is exactly `{{secrets/<scope>/<key>}}`, and point each task at it. With kedro-databricks, put both under the default job in `conf/<env>/databricks.yml`:

     ```yaml
     resources:
       jobs:
         default:
           environments:
           - environment_key: default
             spec:
               dependencies:
               - ../dist/*.whl
               environment_version: '5'
           environment_variables:
           - environment_variables_key: secrets
             spec:
               variables:
                 DB_PASSWORD: '{{secrets/<scope>/<key>}}'
           tasks:
           - task_key: default
             environment_key: default
             environment_variables_key: secrets
     ```

     This is a Beta feature that a workspace admin may need to turn on, and secrets are resolved as the job's run-as identity: link `https://docs.databricks.com/aws/en/jobs/environment-variables`. On classic job clusters the same reference goes in `spark_env_vars` instead: link `https://docs.databricks.com/aws/en/security/secrets/secrets-spark-conf-env-var`.
  2. Register a custom resolver in `settings.py` (`CONFIG_LOADER_ARGS["custom_resolvers"]`) that reads the scope, and use it only in `conf/<env>/credentials.yml`, for example `password: ${dbx_secret:<scope>,<key>}`. Give it a local fallback, because the check below and `kedro databricks bundle` load the configuration (and run hooks) on the developer's machine:

     ```python
     import os


     def databricks_secret(scope: str, key: str) -> str:
         if "DATABRICKS_RUNTIME_VERSION" not in os.environ:  # not running on Databricks
             return "local-placeholder"
         from databricks.sdk.runtime import dbutils

         return dbutils.secrets.get(scope=scope, key=key)
     ```
- Unset `${oc.env:...}` variables fail when configuration is loaded locally. Set dummy values locally and in CI.
- The project template gitignores `conf/**/*credentials*`. A references-only `conf/<env>/credentials.yml` needed in CI needs a `.gitignore` exception, and must never contain values.
- Creating secret scopes and setting their permissions belongs to Databricks.

## How nodes map to jobs and tasks

- kedro-databricks makes one Databricks job per registered pipeline: `__default__` becomes `<package>`, and pipeline `x` becomes `<package>_x`.
- `-g/--resource-generator` sets the task granularity:
  - `node` (the default): one task per node, running `kedro run --nodes <node>`, with `depends_on` taken from the node dependencies.
  - `pipeline`: one task per job, running `kedro run --pipeline <name>`. Kedro marks `--pipeline` as deprecated since 1.4.0; the warning in the task log is harmless for now.
  - The dotted import path of your own `AbstractResourceGenerator` subclass (see the plugin's user guide).
- There is no built-in namespace generator in kedro-databricks 0.18.x. For one job with a task per namespace, write a custom generator, or write the job by hand: one `python_wheel_task` per group running `--namespaces <group>`, with `depends_on` taken from `group.dependencies` in the snapshot below. Registering each namespace as its own pipeline and using `-g pipeline` gives separate single-task jobs, which Databricks does not order.
- `-g node` refuses, at bundle time, any dataset that is undeclared or a `MemoryDataset` in **any** registered pipeline, including final outputs that no other task reads. `-g pipeline` allows them, because everything stays in one task.
- Name nodes and use namespaces before deploying: unnamed nodes get hashed task names.
- More tasks mean more environment start-ups: each serverless task installs the job environment, so even a node that runs in a second takes tens of seconds as a task. A task per node is rarely right for a large pipeline; a task per pipeline or per namespace usually is. Databricks Free Edition runs at most 5 job tasks at once per account (`https://docs.databricks.com/aws/en/getting-started/free-edition-limitations`), so wide per-node jobs queue there.

## Check before deploying

Steps 1 and 2 below need Kedro 1.8.0 or later; the `grouping check` line printed under "Step 1: check what is installed" says whether the installed Kedro has them. On an older Kedro, say the grouping check is not available yet and go on to step 3: with `-g node`, kedro-databricks still refuses in-memory datasets when it generates the bundle.

Do these in order, using the environment the job will use (`<env>`), never `local`:

**1. List the groups.** Groups are what a deployment can run as separate tasks:

```python
from pathlib import Path
from kedro.inspection import get_project_snapshot

snapshot = get_project_snapshot(Path.cwd(), env="<env>")  # group_by="namespace" is the default
for pipeline in snapshot.pipelines:
    print(pipeline.name)
    for group in pipeline.groups:
        print(" ", group.name, "after:", group.dependencies, "in:", group.inputs, "out:", group.outputs)
```

Use `group.dependencies` for the run order: groups are listed in order of their first node.

**2. Check the grouping against the deploy environment's catalog.** Pass `group_by=None` when the tasks will be one per node (`-g node`), or `"namespace"` for namespace groups. With `-g pipeline` each job is a single task, so skip this step and only make sure the pipelines' inputs and outputs are on a volume.

```python
from pathlib import Path
from kedro.framework.project import pipelines
from kedro.framework.session import KedroSession
from kedro.framework.startup import bootstrap_project
from kedro.inspection import validate_deployment_grouping

bootstrap_project(Path.cwd())
with KedroSession.create(env="<env>") as session:
    catalog = session.load_context().catalog
failed = False
for name, pipeline in pipelines.items():  # each registered pipeline becomes its own job
    result = validate_deployment_grouping(pipeline, catalog, group_by=None)
    for issue in result.issues:
        print(name, issue.severity, issue.code, issue.datasets, issue.message)
    failed = failed or not result
raise SystemExit(1 if failed else 0)
```

- `ephemeral_boundary` errors and `local_boundary` warnings: a dataset passed between tasks is only in memory, or on local disk. Declare it on a volume in `conf/<env>/catalog.yml`, or put the nodes that use it in one group. A dataset factory such as `"{split}_train"` with a `${_file_path}/...` filepath covers several datasets and satisfies kedro-databricks' check too.
- `group_cycle` errors: a node outside a namespace sits between nodes inside it. Move that node into the namespace, or split the namespace.
- `invalid_grouping` only appears when you pass your own `groups=`. The `info` issue `single_node_groups` needs no change.
- Run the check again after each fix. The exit code is non-zero while errors remain, so the same snippet works in CI.
- The check only covers datasets that cross task boundaries. It does not report pipeline inputs (such as raw data) or final outputs that are still on local paths, and it treats `/dbfs/`, `dbfs:/` and `/Workspace/` paths as shared, so check those against the Storage rules yourself. For `-g node`, kedro-databricks also needs final outputs declared.
- The project's code must import: PySpark projects need `pyspark` locally, or `databricks-connect` in a Databricks Connect environment, never both. Project hooks run and credentials are resolved, so set dummy values for `${oc.env:...}` variables.
- Kedro logs to stdout. To parse the results, write each `json.dumps(result.to_dict())` to a file.

**3. Generate the bundle:** `kedro databricks bundle -e <env> -g <node|pipeline> --overwrite`. Use `-g node` only once step 2 passes and final outputs are declared; otherwise use `-g pipeline`. If the project has no `databricks.yml` yet, run `kedro databricks init` first. Read the generated `resources/target.<env>.jobs.*.yml` and explain them to the user.

**4. Validate the bundle:** `databricks bundle validate -t <env>`, with `--strict` if `validate --help` lists it. kedro-databricks' `deploy` does not validate first. The `prod` target that `init` generates deploys to `/Workspace/Shared`, which every workspace user can write, so `--strict` fails on it. Adding explicit `permissions` or moving `root_path` under `/Workspace/Users/...` is a permissions decision: link `https://docs.databricks.com/aws/en/dev-tools/bundles/permissions`.

**5. Deploy and run:** `kedro databricks deploy -e <env>`, then `kedro databricks run -e <env>`. For a non-default pipeline pass the full job key, `<package>_<pipeline>`, even though the plugin's docs show the pipeline name. `kedro databricks run` waits for the job and prints only the last task's log, rendered as HTML; for other tasks use the run page or `databricks jobs get-run-output <task run id>`. When `conf/<env>/catalog.yml` has a `_file_path` key, `deploy` also copies the local `data/` folder to `<_file_path>/data` on the volume, overwriting files of the same name. Check what is in `data/` before deploying to a shared or production target. Arguments after `--` go to both `databricks bundle deploy` and that upload (`databricks fs cp`), so pass only flags both accept, such as `--profile`. A bundle-only flag such as `--force-lock` makes the upload fail with `unknown flag` after the bundle has already been deployed.

## CI

kedro-databricks generates no CI workflow. A runner that deploys needs the Databricks CLI, Kedro and the project's dependencies (for `kedro package`), and should deploy a committed target. Run the check above and `databricks bundle validate` before `deploy`. Authentication for CI (service principals, OAuth, OIDC) belongs to Databricks: link `https://docs.databricks.com/aws/en/dev-tools/ci-cd/`.

## Out of scope: defer to Databricks

Answer these by saying where the setting lives and linking the Databricks documentation. Do not write the values yourself.

Compute settings live in `conf/<env>/databricks.yml`. Entries under `resources.jobs.default` apply to every generated job, a task with `task_key: default` applies to every task, and keys starting with `re:` match job or task names by regex (`--default-key` and `--regex-prefix` change these names). `kedro databricks init` puts a serverless `environments` entry there. To change compute, edit that entry using the pages below, then regenerate.

- Compute and cluster configuration: serverless or job clusters, node types, autoscaling, runtime and environment versions, policies. See `https://docs.databricks.com/aws/en/compute/configure`, `https://docs.databricks.com/aws/en/jobs/compute` and `https://docs.databricks.com/aws/en/admin/clusters/policies`.
- Job permissions and `run_as`: `https://docs.databricks.com/aws/en/dev-tools/bundles/permissions` and `https://docs.databricks.com/aws/en/dev-tools/bundles/run-as`
- Unity Catalog grants: `https://docs.databricks.com/aws/en/data-governance/unity-catalog/manage-privileges/`
- Authentication and CLI profiles: `https://docs.databricks.com/aws/en/dev-tools/auth/`
- Secret scopes: `https://docs.databricks.com/aws/en/security/secrets/`
- Bundle syntax and deploy errors, including Terraform errors on older CLIs: `https://docs.databricks.com/aws/en/dev-tools/bundles/`
- Networking, quotas and workspace administration.

For platform-only work, Databricks publishes its own agent skills (`databricks aitools install`, Databricks CLI v1.0 or later). Suggest them as optional; this skill stays responsible for the Kedro side.

## When unsure

The installed code and `--help` output win over this file. Say what you could not check rather than guessing, and label behaviour by version ("in kedro-databricks 0.18.x ...").

Verified against Kedro `main` before the 1.8.0 release, kedro-databricks 0.18.3 and Databricks CLI v1.22.0, deploying spaceflights-pyspark to Databricks Free Edition on 23 October 2026.
