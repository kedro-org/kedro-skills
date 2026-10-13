import pandas as pd
from langchain_core.tools import tool as langchain_tool


def build_lookup_docs(docs: pd.DataFrame, max_matches: int):
    @langchain_tool
    def lookup_docs(query: str) -> str:
        """Return the documents whose text mentions the query."""
        hits = docs[docs["text"].str.contains(query, case=False, na=False)]
        return "\n".join(hits["text"].head(max_matches))

    return lookup_docs
