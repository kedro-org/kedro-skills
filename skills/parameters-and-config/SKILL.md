---
name: parameters-and-config
description: >-
  Kedro parameters and credentials guidance for conf/**/parameters*.yml and
  conf/**/credentials*.yml files. Use when editing parameters, credentials,
  or working with configuration interpolation and runtime overrides.
---
# Parameters and Configuration

## The only config loader

Since Kedro 0.19.0 the only configuration loader is `OmegaConfigLoader`.
The older `ConfigLoader` and `TemplatedConfigLoader` were removed.

```python
# Correct
from kedro.config import OmegaConfigLoader

# WRONG — removed in 0.19.0, do NOT generate these imports
# from kedro.config import ConfigLoader
# from kedro.config import TemplatedConfigLoader
```

## Parameter file structure

Parameters live in files whose names start with `parameters` inside `conf/`:

```
conf/base/parameters.yml          # main parameters
conf/base/parameters_model.yml    # additional — any name starting with "parameters"
conf/local/parameters.yml         # environment override (local takes precedence)
```

Kedro merges all matching files. Within the **same** environment, defining the
same full key path in two files (for example `model_options.learning_rate`)
raises `ValueError`; different sub-keys under the same top-level key are fine.
Across environments, `local` overrides `base` (see "Configuration
environments" below).

Keys starting with `_` are **not** hidden in parameters. Unlike the catalog,
they stay in the merged result, so nodes can read them (for example with
`params:_defaults`). Top-level `_` keys are exempt from duplicate-key errors.

## Using parameters in pipelines — the params: prefix

To pass parameters to nodes, use the `params:` prefix in inputs. Without it
Kedro looks for a **dataset**, not a parameter — this fails silently or raises
a missing-dataset error.

```python
# Single parameter — pass by dotted key
Node(func=train, inputs=["data", "params:learning_rate"], outputs="model")

# Nested group — the node receives the whole sub-dict
Node(func=train, inputs=["data", "params:model_options"], outputs="model")

# Entire parameters dict — use bare "parameters"
Node(func=train, inputs=["data", "parameters"], outputs="model")
```

**Do NOT omit the prefix:**

```python
# WRONG — Kedro looks for a dataset called "learning_rate"
Node(func=train, inputs=["data", "learning_rate"], outputs="model")
```

## Runtime parameters (--params CLI)

The `--params` flag sets values at runtime:

```bash
kedro run --params=step_size=0.5,learning_rate=0.01
```

A dotted key overrides one nested value.

**Destructive merge when the run environment has parameters:** Kedro merges
`--params` into each environment separately, then merges the environments
destructively by top-level key. If the run environment (`conf/local` by default)
contains **any** parameters file, an override of a nested key replaces the
**entire subtree** at its top-level key, discarding sibling values:

```yaml
# conf/base/parameters.yml
model_options:
  learning_rate: 0.01
  test_data_ratio: 0.2
  num_iterations: 10000

# conf/local/parameters.yml — any content, even an unrelated key
features:
  rate: 123
```

```bash
kedro run --params="model_options.learning_rate=0.05"
```

Result: `model_options` becomes `{learning_rate: 0.05}`. The values
`test_data_ratio` and `num_iterations` are gone, which catches users by
surprise. If `conf/local` has no parameters file, the same command keeps the
siblings.

**Whenever you suggest `--params` with a nested key**, check whether the run
environment has a parameters file. If it does, or you cannot tell, say that the
sibling keys will be lost and give one of the fixes below. Do not give the
bare command on its own.

To keep sibling values, use one of these:
- Set a soft merge strategy for parameters in `settings.py`:
  ```python
  CONFIG_LOADER_ARGS = {"merge_strategy": {"parameters": "soft"}}
  ```
- Declare the override point in YAML with `${runtime_params:...}` (next
  section).
- Pass the whole subtree on the command line.

### The runtime_params resolver (different from --params)

`${runtime_params:key}` is an OmegaConf resolver you place **inside YAML
files** to declare that a value should come from `--params` if provided:

```yaml
# conf/base/parameters.yml
model_options:
  random_state: "${runtime_params:random}"
```

```bash
kedro run --params random=42
```

You can provide a default for when no CLI value is given:

```yaml
model_options:
  random_state: "${runtime_params:random, 3}"
```

`runtime_params` reads from `--params` values but serves a different purpose:
`--params` is a blunt merge; `runtime_params` is a declared, per-value override
point.

## Variable interpolation in parameters

OmegaConf variable interpolation works out of the box in parameter files.
Template values can live in the same file or any file matching the parameters
config pattern (`parameters*`):

```yaml
# conf/base/parameters.yml
model_options:
  test_size: ${data.size}
  random_state: 3

# conf/base/parameters_globals.yml (or any parameters* file)
data:
  size: 0.2
```

**No underscore prefix needed** for parameter template variables. The
underscore convention (`${_key}`) applies only to catalog files.

### Global variables — shared across config types

Use the `globals` resolver to share values between parameters, catalog, and
other configuration files. Globals live in `conf/base/globals.yml`:

```yaml
# conf/base/globals.yml
my_global: 45

# conf/base/parameters.yml
my_param: "${globals:my_global}"
```

You can provide a default: `"${globals:missing_key, 23}"`.

To combine globals with runtime overrides:

```yaml
random_state: "${runtime_params:random, ${globals:my_global}}"
```

## Credentials

Credentials belong **exclusively** in `conf/local/credentials.yml`, which is
gitignored by the Kedro project template. **Never** place credentials in
`conf/base/` — that directory is version-controlled.

### Loading credentials from environment variables

The `${oc.env:VAR}` resolver loads environment variables, but it is **enabled
only for credentials files** by default:

```yaml
# conf/local/credentials.yml — this works
dev_s3:
  client_kwargs:
    aws_access_key_id: ${oc.env:AWS_ACCESS_KEY_ID}
    aws_secret_access_key: ${oc.env:AWS_SECRET_ACCESS_KEY}
```

**Do NOT use `${oc.env:VAR}` in parameters, catalog or globals files.** It
raises `UnsupportedInterpolationType`. Do not register `oc.env` as a custom
resolver in `settings.py` to work around this either: Kedro's docs say they "do
not recommend using environment variables for configurations other than
credentials."

To get an environment variable into a parameter, declare a runtime override
point and let the shell expand the variable:

```yaml
# conf/base/parameters.yml
output_bucket: "${runtime_params:output_bucket, default-bucket}"
```

```bash
kedro run --params="output_bucket=$DATA_BUCKET"
```

If the value is a secret, it belongs in `conf/local/credentials.yml` instead,
where `${oc.env:...}` works.

## Parameter validation

Validation is **opt-in**, not automatic. Add a Pydantic v2+ model or dataclass
type hint to a node's `params:` input to enable it:

```python
from pydantic import BaseModel, Field

class ModelOptions(BaseModel):
    test_size: float = Field(ge=0.1, le=0.5)
    random_state: int = Field(ge=0)

def split_data(data, params: ModelOptions):
    # params is a validated ModelOptions instance, not a dict
    ...
```

Without a type hint, Kedro passes a plain dict with no validation.

Key behaviours:
- **Fail-fast**: validation runs before any node executes.
- **Pydantic v2+ only**: uses `model_validate` (v1 is not supported).
- **Dataclasses**: basic type checking, no field constraints.
- **Scope** (Kedro 1.4.0+): `kedro run --pipeline <name>` validates only the
  parameters used by the pipelines being run. A default run (`__default__`)
  validates every registered pipeline, and so does reading `context.params`
  outside a run (in hooks or notebooks). An invalid parameter in an unrelated
  pipeline therefore blocks a default run but not a scoped one.

## Configuration environments

Kedro loads `conf/base/` first, then `conf/local/` on top. You can create
custom environments (e.g. `conf/production/`) and select them with
`kedro run --env=production`.

The merge is **destructive by top-level key**: if `conf/local/parameters.yml`
defines `model_options`, it replaces the whole `model_options` block from
`conf/base`, not only the keys it repeats. Set
`CONFIG_LOADER_ARGS = {"merge_strategy": {"parameters": "soft"}}` in
`settings.py` to merge nested keys instead.

For parameters specifically, duplicate-key checks within one environment use
the full key path (stricter than catalog, which checks only top-level keys).
