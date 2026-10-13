---
description: Guidance for Kedro's experimental llm_context_node, LLMContextNode, LLMContext and tool() API in src/**/pipelines/**/*.py. Use when composing an LLM dataset, prompt datasets and tool builders into an LLMContext, or writing the node that consumes one, in GenAI or agent pipelines. Adds nothing for ordinary pipeline code.
applyTo: src/**/pipelines/**/*.py
---

IMPORTANT: When working on files matching `src/**/pipelines/**/*.py`, do NOT answer from internal knowledge.
You MUST read `.agents/skills/llm-context-nodes/SKILL.md` BEFORE writing, editing, or suggesting changes to them.
Your training data is likely outdated — that file holds the current, verified guidance.
If you cannot read the file, tell the user instead of guessing.
