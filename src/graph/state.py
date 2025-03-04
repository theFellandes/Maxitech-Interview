"""
This module contains the GraphState class, which represents the state of our graph.
"""
from typing import List, TypedDict, Optional
from langchain_core.documents import Document


class GraphState(TypedDict):
    """
    Represents the state of our graph.

    Attributes:
        chat_history: Chat history
        original_question: Question from the user
        clarified_question: Clarified question
        wikipedia_docs: Wikipedia documents
        web_docs: Web documents from Tavily
        reranked_docs: Reranked documents
        final_answer: Final answer
        needs_clarification: Whether the question needs clarification
        session_id: Session ID
    """
    chat_history: List[str]          # Stores all previous messages (user & bot)
    original_question: str
    clarified_question: Optional[str]
    wikipedia_docs: List[Document]
    web_docs: List[Document]
    reranked_docs: List[Document]
    final_answer: Optional[str]
    needs_clarification: bool
    session_id: str
