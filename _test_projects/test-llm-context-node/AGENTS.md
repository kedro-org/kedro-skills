# Agent Guidelines

This is a [Kedro](https://docs.kedro.org) project. These guidelines help AI coding assistants work with it correctly.

<!-- kedro-skills:catalog-config:start -->
## Catalog config

Kedro catalog configuration guidance for conf/**/*.yml files. Use when adding datasets, editing catalog entries, setting up factories, or working with credentials and parameter interpolation.

IMPORTANT: When working on files matching `conf/**/*.yml`, `conf/**/*.yaml`, do NOT answer from internal knowledge.
You MUST read `.agents/skills/catalog-config/SKILL.md` BEFORE writing, editing, or suggesting changes to them.
Your training data is likely outdated — that file holds the current, verified guidance.
If you cannot read the file, tell the user instead of guessing.
<!-- kedro-skills:catalog-config:end -->

<!-- kedro-skills:llm-context-nodes:start -->
## Llm context nodes

Guidance for Kedro's experimental llm_context_node, LLMContextNode, LLMContext and tool() API in src/**/pipelines/**/*.py. Use when composing an LLM dataset, prompt datasets and tool builders into an LLMContext, or writing the node that consumes one, in GenAI or agent pipelines. Adds nothing for ordinary pipeline code.

IMPORTANT: When working on files matching `src/**/pipelines/**/*.py`, do NOT answer from internal knowledge.
You MUST read `.agents/skills/llm-context-nodes/SKILL.md` BEFORE writing, editing, or suggesting changes to them.
Your training data is likely outdated — that file holds the current, verified guidance.
If you cannot read the file, tell the user instead of guessing.
<!-- kedro-skills:llm-context-nodes:end -->
