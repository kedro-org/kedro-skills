---
name: build-demo
description: >-
  Builds a new, small, end-to-end Kedro demo for someone's use case, with a
  working project, a Kedro-Viz walkthrough and optional material for the
  audience. Use when someone asks for a Kedro demo or proof of concept, or
  wants to see whether and how Kedro would work for their problem. Not for
  changing or explaining an existing project.
---
# Build a Kedro demo

## Scope

The outcome is a new Kedro project that runs end to end, saves a result that answers the user's question, loads in Kedro-Viz, and has a `DEMO.md` that walks through it. Slides, diagrams or a technical overview are extras, made only when asked.

- Build in a new folder, or in a fresh blank project the user created for the demo (template files only, no pipelines yet). If the current folder is a project with real pipelines, leave it untouched and ask where the demo should go.
- For a question only about whether Kedro fits, answer it (step 1) and offer to build. Create nothing yet.
- Out of scope: changing or explaining an existing project (`explain-project` covers explaining), deployment, production hardening and serving live requests.

**CRITICAL:**
- Say plainly where Kedro helps and where it does not.
- A demo "works" only for the exact command you ran and whose result you inspected. If something blocked the run, hand it over as prepared but unverified.
- Keep real secret values out of code, docs, outputs and shareable configuration. Reference them by name; ignored local credential files are fine. Never open, print or grep a credential file such as `conf/local/credentials.yml` or `.env` (step 4).
- Before writing any file, show a short plan, even if you continue straight away.
- Label every simulated component wherever it appears.
- Get the user's OK before installing packages or making paid or external calls, unless they already gave it.

## 1. Understand the request and Kedro's role

Take what the request already says, then establish:

- the use case and the result they want to see. That may be a cleaned table, an aggregate, a report, a score or an evaluation;
- the data: theirs, or a generated sample;
- the stack or framework they use or prefer;
- who will watch the demo, when that changes what you deliver;
- constraints such as no API key, no network or limited time;
- how they will judge that it works.

Judge what Kedro would add to this use case:

- **Kedro helps** where the work has steps worth separating, must rerun the same way, is shared by a team, or runs as a batch: ingesting, transforming, training, indexing, evaluating, scoring. One of these is enough.
- **Single-step or one-off work** is not automatically a poor fit. Say what Kedro would add, such as a catalog, parameters, a reproducible rerun or the graph, and let the user decide.
- **Mixed requests:** a chatbot or API usually has batch parts, such as preparing and indexing documents, evaluating answers or batch classification. Offer to build those in Kedro and say that serving the live requests stays outside this demo. Do not silently replace the workflow the user asked for.
- **No useful role:** explain why in two or three sentences and what would change that. Build only if the user still wants a demo.

Ask only questions whose answers change the design. When fit is clear, send them together with the plan from step 2. When fit depends on an answer, ask that first. For anything with a sensible default, state the default instead of asking.

## 2. Plan the demo story

Show the user a short plan, in the same message as any questions. If nothing needs asking, state the plan in a few lines and continue:

- the story in one sentence;
- inputs → stages → result, with the dataset names;
- where the data comes from;
- the exact run command and its mode, and for GenAI whether the model is live, local or simulated;
- packages to install and keys needed;
- the deliverables.

Use the smallest design a viewer can follow, where each stage is a step they can name. One pipeline may be enough. Two to four pipelines and up to about fifteen nodes is usually plenty, running in a minute or two.

Pick only the features that make this use case clearer, based on why the user is looking at Kedro:

| They care about | Possible demonstration |
|---|---|
| Reproducibility | Inputs and outputs in the catalog, parameters in YAML, `versioned: true` on the result, a clean rerun |
| Team work | One pipeline per stage, configuration separate from code, the graph in Kedro-Viz |
| Changing settings | `kedro run --params "<key>=<value>"` changing the result without code changes |
| Moving to the cloud | The same code with a catalog `filepath` on cloud storage. That needs the filesystem package (such as `s3fs`) and credentials. |
| Governance and data quality | Credentials outside code, lineage in Kedro-Viz, versioned outputs, dataset validation (a `validator` in the catalog entry, Kedro 1.6+) |
| Experiment tracking | A tracking plugin such as `kedro-mlflow`. Kedro-Viz experiment tracking and the `tracking.*` datasets were removed. |

Default to a small, realistic, generated sample with a fixed seed, described as synthetic in `DEMO.md`. Use the user's data only if they provide it, and keep sensitive data out of git. Use a public dataset only when its licence allows it and it can be downloaded.

A request to build a demo covers creating the folder and its files. Settle choices that change the build before you start.

## 3. Prepare the environment and project

Check versions with the interpreter you will use:

```bash
python -c "import sys, importlib.metadata as m; print(sys.executable); print({p: next((d.version for d in m.distributions(name=p)), None) for p in ('kedro', 'kedro-datasets', 'kedro-viz')})"
```

Propose a fresh virtual environment with current, compatible `kedro`, `kedro-datasets` and `kedro-viz` if any of these is true:
- the interpreter is not inside a virtual or conda environment;
- Kedro is missing;
- Kedro is too old for the features you plan to use.

Take all versions from that one interpreter.

Create the project without prompts:

```bash
kedro new --name "<Demo name>" --tools data --example n
```

This creates a `<demo-name>` folder in the current directory, with `data/01_raw` to `data/08_reporting`. Add `test` to `--tools` if you will write tests. Pass `--telemetry` only when the user has stated a preference. In a fresh blank project the user already created, skip this step and inspect its files.

Add each pipeline with `kedro pipeline create <name>`. This creates the pipeline package, `conf/base/parameters_<name>.yml` and a test folder. `find_pipelines()` in the template registers it, and `__default__` runs them all.

The template's `requirements.txt` lists only Kedro and Jupyter. Add:
- `kedro-datasets[<extra>]` for each dataset type, for example `pandas-csvdataset` or `json-jsondataset`;
- `kedro-viz`;
- the libraries your nodes import.

Install them once the user agrees.

## 4. Build the demo

- **Nodes:** small functions named for what they do.
  - Give every node `name=`, because an unnamed node shows as `<function>__<hash>`.
  - Keep model calls, data loading and heavy work out of import time, so `kedro registry list` and Kedro-Viz can load the project.
- **Catalog:** add an entry for every input and every result worth showing. Data that stays in memory is fine between steps, but say so in the walkthrough.
  - Choose a dataset whose save method accepts the node's output: a DataFrame to `pandas.CSVDataset` or `pandas.ParquetDataset`, JSON-serialisable data to `json.JSONDataset`, a Plotly figure to `plotly.JSONDataset`, a Matplotlib figure to `matplotlib.MatplotlibDataset`.
  - Some types are read-only, such as `pandas.SQLQueryDataset`.
  - Follow `catalog-config` when it is installed, otherwise the kedro-datasets docs.
- **Parameters:** put tunable values in the parameters files and read them as `params:<key>`. Keep each top-level group in one file. If another environment overrides a group, the default merge replaces the whole group, so repeat its other keys there. Follow `parameters-and-config` when it is installed.
- **Credentials:** reference them by name, and tell the user which keys to fill in.
  - Name the credential keys your catalog references, for example `credentials: openai`, and ask the user to confirm they exist.
  - `conf/local/credentials.yml` (gitignored) is read only in the default run environment.
  - With `--env <name>`, use environment variables or that environment's credentials file.
- **Sample data:** the template's `.gitignore` excludes everything under `data/`. To ship an approved synthetic sample, add a `!data/01_raw/<file>` line, or include the command that regenerates it. Keep private inputs and outputs ignored, and leave committing to the user.

Where they help the story, make the graph easier to read in Kedro-Viz:

- **Layers.** For a dataset whose `preview` accepts `nrows`, such as `pandas.CSVDataset`, add this to its catalog entry, choosing a layer such as `raw`, `intermediate`, `primary`, `feature`, `model_input`, `models`, `model_output` or `reporting`:

  ```yaml
  metadata:
    kedro-viz:
      layer: raw
      preview_args:
        nrows: 5
  ```

  For other types, use their documented preview arguments, or keep only `layer`.
- **Groups.** You can make each stage its own registered pipeline. Or wrap it with `Pipeline([...], namespace="<stage>", prefix_datasets_with_namespace=False)` (Kedro 1.0+), which shows the stage as one collapsible block and keeps dataset and parameter names unchanged.
  - Node names still get the `<stage>.` prefix.
  - Without the flag, unmapped dataset names and `params:` references gain the prefix, for example `params:stage.factor`. The catalog and parameter keys must then match.
- **Node explanations (optional, experimental).** `Node(..., preview_fn=<function>)` (Kedro 1.2+, shown by Kedro-Viz 12.3+) takes a pure function with no arguments that returns either:
  - `TextPreview(content=...)`: a sentence on what the step means for the use case; or
  - `MermaidPreview(content=...)`: for example, the intended steps inside an agent node.

  Import them from `kedro.pipeline.preview_contract`. They are authored explanations, not execution traces. Kedro logs a one-time experimental warning; mention it in `DEMO.md`.

### 4a. GenAI, only when relevant

- **Kedro's part.**
  - Keep the user's framework and provider.
  - Kedro runs the stages around the model: loading and chunking documents, building an index, batch classification or extraction, running an evaluation set, saving results.
  - An agent's own loop runs inside one node and does not appear as separate graph nodes. A `MermaidPreview` can sketch it.
  - Keep the calls bounded: no open-ended loops or repeated retries.
- **Model access.** kedro-datasets provides `langchain.ChatOpenAIDataset`, `langchain.ChatAnthropicDataset`, `langchain.ChatCohereDataset` and `langchain.OpenAIEmbeddingsDataset`. Experimental Langfuse and Opik prompt and trace datasets also exist. Use the one that matches the user's stack, and check its type name and extra in the installed version's docs. Keep model clients and context objects in memory (`MemoryDataset` with `copy_mode: assign`).
- **LLM context nodes.** Use `llm_context_node` (Kedro 1.2+) only when a node needs an LLM with prompts or tools bundled, and follow `llm-context-nodes` when it is installed. The `support-agent-langgraph` starter is a full reference.
- **Execution mode.** Name it:
  - **live:** a real provider. It needs a key, can cost money and needs an OK first.
  - **local:** a model running on the machine.
  - **simulated:** a deterministic stand-in so the demo runs without a key. It is optional, and must never quietly replace a capability the user asked to see.

  If the user asked for a model or provider you can't use here (no key, no installs, no calls), ask before adding a simulated stand-in. Without an answer, prepare the live path, leave it unrun, and hand over as prepared but unverified.

  Make the mode you will verify the default for a plain `kedro run`. Switch the others with `--params` or `--env <name>`. Label a simulated mode in the code, in the outputs (for example a `mode` field) and in `DEMO.md`. A simulated run passing does not show that the live integration works.

## 5. Verify the chosen path

From the project folder, using the project's interpreter:

1. Run `kedro registry list` and check that every planned pipeline is listed. The template's `find_pipelines(raise_errors=True)` fails loudly on import errors.
2. Run the exact command for the chosen mode, including any `--env` or `--params`. Open the saved result and check that it answers the user's question: not empty, and with plausible values.
3. If `DEMO.md` shows a `--params` override, run it and confirm that the result changes. If it doesn't, remove it from `DEMO.md` or choose one that does.
4. Optionally run `kedro viz build` as a finite check that the graph loads.
   - It finishes in seconds and writes the gitignored `build/` folder.
   - It uses the default configuration only, with no `--env` or `--params`.
   - It can print `ERROR: Failed to build/deploy Kedro-Viz` and still exit 0. Look for its success line and for `build/api/main`.
   - If the demo's mode needs other options, say that Viz was checked with the defaults only.
   - Start `kedro viz run`, which is a server, only when the user asks, and stop it afterwards.
5. Check that code, docs, outputs and shareable configuration contain no secret values, without printing any. In a git repository, confirm with `git check-ignore` that credential files are ignored.
6. Add tests only for logic worth protecting.

Fix failures within scope. If a prerequisite is missing (a key, a package that will not install, no network), stop and say what is missing and what was verified, instead of retrying live services. Note the command you ran, its mode and what you saw. `DEMO.md` and the handover use these notes.

## 6. Make Kedro-Viz tell the story

Write `DEMO.md` in the project root and add a one-line pointer to it at the top of `README.md`:

1. **The story:** the problem, what the demo does and the result.
2. **Setup and run:** environment, install, the exact run command, `kedro viz run`, keys needed and the execution mode.
3. **Walkthrough, using the real names:**
   - where to start (the raw input);
   - each group or stage and what it means for the use case;
   - the path from producer to consumer up to the result, where sibling outputs branch rather than chain;
   - the node to click for the key step;
   - which dataset preview or node explanation to open;
   - where the result is saved;
   - what the graph does not show: code inside a node, and live parts outside Kedro.
4. **Things to try:** change a parameter, rerun, compare the versioned outputs.
5. **Limits:** what is synthetic or simulated, and what was not verified.

`kedro viz run` shows dataset previews. `kedro viz build` includes them only with `--include-previews`. Name only the previews and explanations you configured.

## 7. Optional audience material

Offer these based on the audience. Make only what the user asks for, in the format they choose:

- **Stakeholders:** two or three slides covering the problem, what the demo shows (one diagram or Viz screenshot) and what Kedro adds for them.
- **Technical users:** a Mermaid architecture diagram (data sources, Kedro pipelines, model provider, systems outside Kedro) and a short implementation overview.

Every claim must match what ran.

## 8. Before handing over, check

- The exact command passed in the stated mode, and you inspected the result.
- The Kedro-Viz graph loads, or you have said what was not checked.
- Names and commands in `DEMO.md` match the catalog, the graph and what you ran.
- No secret values are in code, docs, outputs or shareable configuration.
- The sample data can be obtained or regenerated.
- Simulated parts are labelled, and unverified parts are listed.

Then hand over in a short message:
- where the project is;
- how to run it and open Kedro-Viz;
- what to look at first;
- the mode you verified;
- limits and next steps.

If the run was blocked, call it a prepared but unverified demo.

## Sources

When this file and the installed code disagree, the installed code wins. Replace `{version}` with the installed Kedro version or `stable`:

- New projects and tools: `https://docs.kedro.org/en/{version}/create/new_project/`
- Kedro-Viz: `https://docs.kedro.org/projects/kedro-viz/en/stable/`
- Dataset types and extras: `https://docs.kedro.org/projects/kedro-datasets/en/latest/`
- LLM context nodes: `https://docs.kedro.org/en/{version}/build/llm_context_node/`
- GenAI reference project: `https://github.com/kedro-org/kedro-starters/tree/main/support-agent-langgraph`
