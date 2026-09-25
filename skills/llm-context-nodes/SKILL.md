---
name: llm-context-nodes
description: >-
  Guidance for Kedro's llm_context_node, LLMContextNode, LLMContext and tool()
  API in src/**/pipelines/**/*.py. Use when composing an LLM dataset, prompt
  datasets and tool builders into an LLMContext, or writing the node that
  consumes one, in GenAI or agent pipelines. Adds nothing for ordinary pipeline
  code.
---
# LLM context nodes

## Scope

**If neither the file nor the request involves `llm_context_node`, `LLMContextNode`, `LLMContext` or `tool` from `kedro.pipeline`, stop here: this skill has nothing to add and must not be mentioned.** Do not suggest converting ordinary nodes into LLM context nodes.

The API was added in Kedro 1.2.0 and its signature has not changed since. Kedro 1.2.0 to 1.6.0 mark it as experimental, and later releases ship it as stable. Check the installed version before writing code, because the API does not exist below 1.2.0.

**CRITICAL:** `LLMContext` has no `execute()`, `run()`, `invoke()` or `stream()`; the downstream node calls `context.llm` and `context.tools[...]` with their own APIs. `context.tools` is keyed by the name of the object a builder *returns*, never by the builder's name. Every parameter passed to `tool(...)` needs the `params:` prefix and must match a builder argument by name.

## Check the installed version once

```bash
python -c "import sys, kedro; print(kedro.__version__, sys.executable)"
```

Your shell may not use the environment the user has activated. If the interpreter path is not inside an environment (it contains `/envs/`, `/.venv/` or `/virtualenvs/`), re-run the command with the project's interpreter directly (`<env-path>/bin/python -c ...` or `conda run -n <env> python -c ...`); if you cannot tell which environment is the project's, ask. If no interpreter works, fall back to the `kedro` pin in `requirements.txt` or `pyproject.toml`.

- **Below 1.2.0**: the API does not exist. Say so, and do not write a backport, a shim or an invented import.
- **1.2.0 or later**: the API below applies. When this file and the installed code disagree, the installed code wins. It is one file of about 300 lines and is the whole feature:

  ```bash
  python -c "import kedro.pipeline.llm_context as m; print(m.__file__)"
  ```

If you cannot run commands, say so and flag that the code was not verified against the installed version.

## The whole API

```python
from kedro.pipeline import LLMContext, LLMContextNode, llm_context_node, tool
```

These four names are the entire surface, and `kedro.pipeline` is where they live (`from kedro.pipeline.llm_context import LLMContext` also works). Import paths such as `kedro.contrib`, `kedro.experimental`, `kedro.llm`, `kedro.pipeline.llm` or `kedro_datasets.llm` do not exist — never generate them.

```python
llm_context_node(
    *,                          # keyword-only; positional arguments raise TypeError
    outputs: str,               # ONE dataset name that receives the LLMContext
    llm: str,                   # dataset name of the LLM object, not the object itself
    prompts: list[str],         # dataset names; required, pass [] if there are none
    tools: list | None = None,  # list of tool(...) configs
    name: str | None = None,    # also becomes context.context_id; always set it
    tags=None, confirms=None, namespace=None, preview_fn=None,  # same as node()
) -> Node
```

There is no `func=` and no `inputs=`: Kedro supplies the function, and the inputs are derived from `llm`, `prompts` and the `tool(...)` entries. Every element of `tools` must be a `tool(builder, *inputs)` object; a bare builder function or a ready-made LangChain tool fails at construction with `AttributeError: 'function' object has no attribute 'inputs'`.

`LLMContextNode(...)` takes exactly the same keyword arguments; it is the class the function wraps, and the two are interchangeable. Both return an ordinary Kedro `Node`.

```python
tool(builder, *inputs: str)  # a config object, not a decorator, not langchain's @tool
```

`LLMContext` is a plain dataclass with four fields and **no methods**:

| Field | Type | Content |
|-------|------|---------|
| `context_id` | `str` | the node `name`, or `llm_context_node__<outputs>` when no name was given |
| `llm` | `object` | whatever the `llm` dataset loaded |
| `prompts` | `dict[str, Any]` | `{prompt dataset name: loaded value}` |
| `tools` | `dict[str, object]` | `{tool name: built tool object}` |

Without `name` the node itself is called `construct_context__<hash>`, which is what `kedro run --nodes` and Kedro-Viz show. Always set it.

## How a context node executes

1. Every name you pass (`llm`, each entry of `prompts`, each input of each `tool(...)`) becomes an ordinary node input. Kedro loads them all from the catalog before the node runs, they appear in the DAG and in Kedro-Viz, and a missing catalog entry or parameter fails the run like it would for any node.
2. At run time each builder is called **once per node run** with keyword arguments named after its declared inputs, with the `params:` prefix stripped:

   ```python
   tool(build_lookup_docs, "docs", "params:max_matches")
   # is called as
   build_lookup_docs(docs=<loaded "docs">, max_matches=<value of params:max_matches>)
   ```

3. The object each builder returns is stored under a name derived from that object: its `__name__` if it has one, else its `.name` attribute, else its class name.
4. The node returns `LLMContext(context_id=..., llm=..., prompts=..., tools=...)` and saves it to the `outputs` dataset.

Nothing is executed. The LLM is not called, prompts are not formatted, tools are not invoked. That is the job of a downstream node.

## Rules

### 1. Never invent execution methods

`LLMContext` has no `execute()`, `run()`, `invoke()`, `call()` or `stream()`. Do not write `context.execute()`, and do not run the LLM through `node.run()`. The node that consumes the context calls the LLM with that LLM's own API, and the tools with theirs:

```python
from kedro.pipeline import LLMContext

def answer(context: LLMContext, question: str) -> str:
    prompt = context.prompts["qa_prompt"].format(question=question)
    evidence = context.tools["lookup_docs"].invoke({"query": question})
    return context.llm.invoke(f"{prompt}\n\n{evidence}").content
```

What `.invoke(...)` accepts and returns depends on the LLM library the `llm` dataset loaded (LangChain chat models expose `invoke`, `stream`, `bind_tools` and `with_structured_output`), not on Kedro. Read that library's docs rather than guessing. The consumption example on the official docs page calls `context.llm.run(prompts=..., tools=...)`; that is illustrative pseudo-code, not a real method. Follow this rule and the example below, not that snippet.

### 2. `llm=` and `prompts=` are dataset names

Write `llm="llm"` and `prompts=["system_prompt"]`, then define those datasets in the catalog. A model object or an inline prompt string fails node validation. A `params:` entry is accepted as a prompt (it lands in `context.prompts["params:system_prompt"]`, prefix included), but it puts prompt text in `parameters.yml` where prompt datasets and Langfuse or Opik versioning cannot see it, so prefer a prompt dataset. `prompts` is required: use `prompts=[]` when there are none.

- The LLM dataset is normally one of the `kedro-datasets` chat datasets, for example `langchain.ChatOpenAIDataset`, `langchain.ChatAnthropicDataset` or `langchain.ChatCohereDataset`, with `credentials:` pointing at `conf/local/credentials.yml`. The credentials mapping is passed straight into the model constructor, so its keys must be constructor arguments (`api_key`, `base_url`). Verify the type exists in the installed `kedro-datasets` before writing the entry (follow the `catalog-config` skill if it is installed).
- Prompt datasets return whatever their type loads: a `str` for `text.TextDataset`, a `PromptTemplate` or `ChatPromptTemplate` for `kedro_datasets_experimental.langchain.PromptDataset`, and provider objects for the `langfuse` and `opik` prompt datasets. The context stores that value unchanged under the dataset's name: `context.prompts["system_prompt"]`.
- **kedro-datasets 9.4.0 renamed the prompt datasets** by dropping the package prefix: `langchain.LangChainPromptDataset` became `langchain.PromptDataset`, `langfuse.LangfusePromptDataset` became `langfuse.PromptDataset`, `opik.OpikPromptDataset` became `opik.PromptDataset` (and the extras changed the same way, for example `langchain-promptdataset`). The Kedro docs page may still show the old names. Check the installed `kedro-datasets` version and use the name that exists in it.

### 3. Tool inputs: `params:` prefix, and names that match the builder's parameters

Every string after the builder in `tool(...)` is a dataset name. A parameter needs the `params:` prefix, exactly as in `node()`:

```python
tool(build_lookup_docs, "docs", "params:max_matches")   # right
tool(build_lookup_docs, "docs", "max_matches")          # wrong: looks for a dataset named max_matches
```

Binding is **by keyword, not by position**: the builder's parameter names must equal the dataset names with `params:` stripped. Order in `tool(...)` is irrelevant. A mismatch is not caught when the node is created, only when the pipeline runs (`TypeError: build_lookup_docs() got an unexpected keyword argument 'docs_table'`), so check the names every time you add or rename an input:

```python
def build_lookup_docs(docs, max_matches: int):   # parameters are named docs and max_matches
    ...

tool(build_lookup_docs, "docs", "params:max_matches")        # right
tool(build_lookup_docs, "docs_table", "params:max_matches")  # wrong: no parameter named docs_table
```

A nested parameter such as `params:retrieval.max_matches` cannot bind to a named argument either, because `retrieval.max_matches` is not a valid argument name (a builder with `**kwargs` receives the dotted key silently, which is worse). Use a top-level key, or pass the parent (`params:retrieval`) and read the key inside the builder.

### 4. Tool names come from the returned object, not from the builder

`context.tools` is keyed by the name of what the builder **returns**. A builder called `build_lookup_docs` that returns a LangChain `@tool` named `lookup_docs` is stored as `context.tools["lookup_docs"]`; `context.tools["build_lookup_docs"]` is a `KeyError`.

```python
from langchain_core.tools import tool as langchain_tool   # alias it: kedro.pipeline also exports a `tool`

def build_lookup_docs(docs, max_matches: int):
    @langchain_tool
    def lookup_docs(query: str) -> str:
        """Return the documents most relevant to the query."""
        return "\n".join(docs.search(query, limit=max_matches))
    return lookup_docs
```

- A plain function is stored under its `__name__`; a LangChain tool under its `.name`; an instance of a class with neither under the class name.
- Two builders returning objects with the same name silently overwrite each other in the dict. Give every tool a distinct name.
- The arguments of the returned tool (`query` above) are supplied by the LLM at execution time, never by Kedro. Only the builder's arguments come from the catalog.

### 5. Tools are built per node run and are not shared

Every context node instantiates its own tools when it runs. Two context nodes declaring the same builder get two independent objects, and re-running a node rebuilds them. Do not treat a tool as a singleton, cache it at module level, or pass a built tool object into `tool(...)`. To share a resource between nodes, share the dataset it is built from (the same `docs` or `db_engine` catalog entry), not the built object.

### 6. One output, kept in memory with `copy_mode: assign`

`outputs` is one string. Even `outputs=["qa_context"]` passes construction and then fails the run with `ValueError: ... The node definition contains a list of outputs ['qa_context'], whereas the node function returned a 'LLMContext'`.

Do not write the context to disk. Leave it as a `MemoryDataset`, but declare it explicitly, because the default `MemoryDataset` deep-copies arbitrary objects on save and load, and real LLM clients cannot be deep-copied (a `ChatOpenAI` client fails with `cannot pickle '_thread.RLock' object`):

```yaml
qa_context:
  type: MemoryDataset
  copy_mode: assign
```

The `support-agent-langgraph` starter instead uses a catch-all factory (`"{default_dataset}"` with `type: MemoryDataset` and `copy_mode: assign`). That is a project-wide decision that changes the copy semantics of every unregistered dataset; in an existing project add the explicit entry for the context dataset instead.

### 7. Namespaces and other `node()` arguments

`name`, `tags`, `confirms`, `namespace` and `preview_fn` behave exactly as on `node()`. Wrapping a context node in `pipeline(..., namespace="rag")` prefixes its datasets and parameters (`rag.docs`, `params:rag.max_matches`) like any other node, while `context.prompts` keeps the keys you declared (`context.prompts["qa_prompt"]`, not `"rag.qa_prompt"`). Two more things stay un-prefixed: `context_id` is the `name=` you passed (`qa_context_node`) even though the node is now `rag.qa_context_node`, and the copied node is a plain `Node`, so find context nodes by name or tag rather than `isinstance(n, LLMContextNode)`. The `namespace=` argument on the node itself only labels the node; it does not rename datasets. Do not put dots in dataset names yourself: Kedro reserves `.` for namespacing and warns about it.

### 8. The experimental warning on Kedro 1.2.0 to 1.6.0

Those releases mark the API as experimental, so `KedroExperimentalWarning: tool is experimental ...`, followed by one warning each for `llm_context_node`, `LLMContextNode` and `LLMContext`, is expected once per process. It is not an error, and it is not a reason to rewrite the node as a plain `node()` or to patch Kedro. Later releases ship the API as stable and emit nothing, so upgrading Kedro removes it. To silence it on an older version:

```python
import warnings
from kedro.utils import KedroExperimentalWarning

warnings.filterwarnings("ignore", category=KedroExperimentalWarning)
```

Passing `preview_fn` still warns on every version, because node previews are a separate experimental feature.

## Complete example

Verified against Kedro 1.6.0 and kedro-datasets 9.6.0.

`conf/base/catalog.yml`

```yaml
llm:
  type: langchain.ChatOpenAIDataset
  kwargs:
    model: gpt-4o-mini
    temperature: 0.0
  credentials: openai

qa_prompt:
  type: kedro_datasets_experimental.langchain.PromptDataset
  filepath: data/01_raw/prompts/qa.txt
  template: PromptTemplate
  dataset:
    type: text.TextDataset

docs:
  type: pandas.CSVDataset
  filepath: data/01_raw/docs.csv

qa_context:
  type: MemoryDataset
  copy_mode: assign
```

`conf/local/credentials.yml` (gitignored; never put it under `conf/base/`)

```yaml
openai:
  api_key: <openai-api-key>
```

`conf/base/parameters.yml`

```yaml
max_matches: 3
```

`src/<package>/pipelines/qa/tools.py`

```python
import pandas as pd
from langchain_core.tools import tool as langchain_tool


def build_lookup_docs(docs: pd.DataFrame, max_matches: int):
    @langchain_tool
    def lookup_docs(query: str) -> str:
        """Return the documents whose text mentions the query."""
        hits = docs[docs["text"].str.contains(query, case=False, na=False)]
        return "\n".join(hits["text"].head(max_matches))

    return lookup_docs
```

`src/<package>/pipelines/qa/nodes.py`

```python
from kedro.pipeline import LLMContext


def answer(context: LLMContext, question: str) -> str:
    prompt = context.prompts["qa_prompt"].format(question=question)
    evidence = context.tools["lookup_docs"].invoke({"query": question})
    return context.llm.invoke(f"{prompt}\n\nEvidence:\n{evidence}").content
```

`src/<package>/pipelines/qa/pipeline.py`

```python
from kedro.pipeline import Pipeline, llm_context_node, node, pipeline, tool

from .nodes import answer
from .tools import build_lookup_docs


def create_pipeline(**kwargs) -> Pipeline:
    return pipeline(
        [
            llm_context_node(
                name="qa_context_node",
                outputs="qa_context",
                llm="llm",
                prompts=["qa_prompt"],
                tools=[tool(build_lookup_docs, "docs", "params:max_matches")],
            ),
            node(answer, ["qa_context", "params:question"], "reply", name="answer_node"),
        ]
    )
```

To unit-test the wiring without a catalog or credentials, pick the node out of the pipeline and run it with plain values keyed by dataset name. `Node.run()` here only builds the context; it never calls the LLM:

```python
from .pipeline import create_pipeline

ctx_node = create_pipeline().only_nodes("qa_context_node").nodes[0]
context = ctx_node.run(
    {"llm": fake_llm, "qa_prompt": "Q: {question}", "docs": docs_df, "params:max_matches": 2}
)["qa_context"]
assert "lookup_docs" in context.tools
assert context.context_id == "qa_context_node"
```

## Dependencies

- `kedro>=1.2.0`.
- The LLM dataset's extra, for example `kedro-datasets[langchain-chatopenaidataset]` or `kedro-datasets[langchain-chatanthropicdataset]`.
- The prompt dataset's extra when prompts are templates, for example `kedro-datasets[langchain-promptdataset]` (`langchain-langchainpromptdataset` before kedro-datasets 9.4.0), and the `langfuse` or `opik` extras for those providers. The `kedro_datasets_experimental.*` prompt datasets ship inside the `kedro-datasets` distribution; there is no separate `kedro-datasets-experimental` package on PyPI, so their extras are installed from `kedro-datasets` too.
- Agent frameworks (LangGraph, OpenAI Agents, AutoGen) are the user's choice for the consuming node. Kedro does not require or bundle any of them.

Suggest updating `requirements.txt` or `pyproject.toml` when you add one of these.

## When unsure

- Read the installed implementation (see "Check the installed version once"). It is short and is the whole feature.
- Documentation, replacing `{version}` with the installed version or `stable`: `https://docs.kedro.org/en/{version}/build/llm_context_node/` (its consumption example uses pseudo-code, see Rule 1).
- Experimental API policy, relevant to Kedro 1.2.0 to 1.6.0 and to `preview_fn`: https://docs.kedro.org/en/stable/about/experimental/
- Reference project using the API end to end with LangGraph, Langfuse and Opik: https://github.com/kedro-org/kedro-starters/tree/main/support-agent-langgraph
