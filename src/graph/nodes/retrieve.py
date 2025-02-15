from typing import Any, Dict

from src.graph.state import GraphState
from src.ingestion.chroma_ingestion import ChromaIngestion

# TODO: Wikipedia API retrieval.
# retriever = ChromaIngestion().insert_documents()


def retrieve(state: GraphState) -> Dict[str, Any]:
    print("---RETRIEVE---")
    question = state["question"]

    # documents = retriever.invoke(question)
    # TODO: Will return the documents from the ingestion or Wikipedia API.
    return {"documents": "documents", "question": question}
