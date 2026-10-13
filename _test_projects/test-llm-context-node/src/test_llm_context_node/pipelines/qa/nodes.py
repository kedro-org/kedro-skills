from kedro.pipeline import LLMContext


def answer(context: LLMContext, question: str) -> str:
    prompt = context.prompts["qa_prompt"].format(question=question)
    evidence = context.tools["lookup_docs"].invoke({"query": question})
    return context.llm.invoke(f"{prompt}\n\nEvidence:\n{evidence}").content
