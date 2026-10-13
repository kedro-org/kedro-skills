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
            node(
                answer,
                ["qa_context", "params:question"],
                "reply",
                name="answer_node",
            ),
        ]
    )
