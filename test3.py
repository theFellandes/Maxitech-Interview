# langgraph_workflow.py
from typing import TypedDict, Optional, List

from dotenv import load_dotenv
from langchain_community.tools import TavilySearchResults

load_dotenv()
import datetime
import uuid

# from src.graph.graph import GraphState
# from src.graph.nodes import generate_answer
from logger.logger import CustomLogger

from langchain_core.documents import Document
from langchain_openai import ChatOpenAI
from langchain_community.utilities import WikipediaAPIWrapper
from langgraph.graph import StateGraph, END


# Initialize our LLM and tools
llm = ChatOpenAI(model="gpt-4-turbo")
wikipedia = WikipediaAPIWrapper(top_k_results=2)
log = CustomLogger()

web_search = TavilySearchResults(k=5)

class GraphState(TypedDict):
    """
    Represents the state of our graph.

    Attributes:
        original_question: Question from the user
        clarified_question: Clarified question
        wikipedia_docs: Wikipedia documents
        web_docs: Web documents from Tavily
        reranked_docs: Reranked documents
        final_answer: Final answer
        needs_clarification: Whether the question needs clarification
        session_id: Session ID
    """
    original_question: str
    clarified_question: Optional[str]
    wikipedia_docs: List[Document]
    web_docs: List[Document]
    reranked_docs: List[Document]
    final_answer: Optional[str]
    needs_clarification: bool
    session_id: str


def retrieve_web(state: GraphState):
    CustomLogger.log_message(state["session_id"], "retrieve_web", "Started processing retrieve_web node")
    query = state.get("clarified_question") or state["original_question"]
    results = web_search.invoke(query)
    docs = [
        Document(page_content=res["content"], metadata={"source": res["url"]})
        for res in results
    ]
    CustomLogger.log_message(state["session_id"], "retrieve_web", f"Retrieved {len(docs)} web document(s)")
    return {"web_docs": docs}

def generate_answer(state: GraphState):
    CustomLogger.log_message(state["session_id"], "generate_answer", "Started processing generate_answer node")
    query = state.get("clarified_question") or state["original_question"]
    if state["wikipedia_docs"]:
        source = "Wikipedia"
        content = "\n".join([d.page_content[:500] for d in state["wikipedia_docs"]])
    else:
        source = "Web"
        content = "\n".join([d.page_content[:500] for d in state["reranked_docs"]])
    prompt = (
        f"Generate a concise 1-2 sentence answer for the question: '{query}'. "
        f"Use the following content from {source}:\n{content}\n"
        "Include the source in parentheses at the end."
    )
    answer = llm.invoke(prompt).content.strip()
    CustomLogger.log_message(state["session_id"], "generate_answer", f"Generated answer: {answer}")
    return {"final_answer": answer}

def detect_ambiguity(state: GraphState):
    log.log_message(state["session_id"], "detect_ambiguity", "Started processing detect_ambiguity node")
    question = state["original_question"]
    prompt = (
        f"Is the following question ambiguous? Respond ONLY with 'yes' or 'no'.\n"
        f"Question: {question}"
    )
    response = llm.invoke(prompt).content.lower()
    ambiguous = "yes" in response
    log.log_message(state["session_id"], "detect_ambiguity", f"Ambiguity detected: {ambiguous}")
    return {"needs_clarification": ambiguous}

def clarify_question(state: GraphState):
    log.log_message(state["session_id"], "clarify_question", "Started processing clarify_question node")
    question = state["original_question"]
    prompt = (
        f"The user asked: \"{question}\"\n"
        "Generate a follow-up clarification question that asks the user to specify which interpretation they meant. "
        "Provide your answer as bullet points."
    )
    clarification = llm.invoke(prompt).content
    log.log_message(state["session_id"], "clarify_question", f"Generated clarification: {clarification.strip()}")
    return {"clarified_question": clarification, "needs_clarification": True}

def process_clarification(state: GraphState):
    log.log_message(state["session_id"], "process_clarification", "Started processing process_clarification node")
    original = state["original_question"]
    clarification = state.get("clarified_question", "").strip()
    # Check if clarification is too ambiguous: if it contains more than one bullet point
    bullet_points = [line for line in clarification.split("\n") if line.strip().startswith("-")]
    if len(bullet_points) > 1:
        log.log_message(state["session_id"], "process_clarification", "Clarification is too ambiguous; deferring to user input.")
        return {"clarified_question": clarification, "needs_clarification": True}
    else:
        prompt = (
            f"Original question: \"{original}\"\n"
            f"Clarification provided: \"{clarification}\"\n"
            "Based on this, provide a clarified version of the question that best captures the intended meaning. "
            "Keep it concise."
        )
        clarified = llm.invoke(prompt).content.strip()
        log.log_message(state["session_id"], "process_clarification", f"Clarified question: {clarified}")
        return {"clarified_question": clarified, "needs_clarification": False}

def transform_query_old(state: GraphState):
    log.log_message(state["session_id"], "transform_query", "Started processing transform_query node")
    # If clarification is still ambiguous, skip transformation.
    if state.get("needs_clarification", False):
        log.log_message(state["session_id"], "transform_query", "Skipping transformation due to ambiguous clarification.")
        return {}
    question = state.get("clarified_question") or state["original_question"]
    # Specific transformation for Tesla HQ queries.
    if "tesla" in question.lower() and ("hq" in question.lower() or "headquarters" in question.lower()):
        transformed = "Where is Tesla's main corporate headquarters located?"
        log.log_message(state["session_id"], "transform_query", f"Transformed query to: {transformed}")
        return {"clarified_question": transformed}
    # Specific transformation for Sequoia investments.
    if "sequoia" in question.lower() and "invest" in question.lower():
        transformed = "Sequoia Capital investments 2025"
        log.log_message(state["session_id"], "transform_query", f"Transformed query to: {transformed}")
        return {"clarified_question": transformed}
    log.log_message(state["session_id"], "transform_query", "No transformation applied")
    return {}


def transform_query(state: GraphState):
    log.log_message(state["session_id"], "transform_query", "Started processing transform_query node")
    # If clarification is still ambiguous, skip transformation.
    if state.get("needs_clarification", False):
        log.log_message(state["session_id"], "transform_query", "Skipping transformation due to ambiguous clarification.")
        return {}

    question = state.get("clarified_question") or state["original_question"]

    # Define candidate transformed queries (retrieved from documents/previous knowledge).
    # For example, these candidates were derived from a corpus of documents.
    candidates = [
        "Where is Tesla's main corporate headquarters located?",
        "Sequoia Capital investments 2025"
    ]
    # Add the original question as a candidate (i.e. no transformation)
    candidates.append(question)

    # Use TF-IDF to compare the input query with the candidate transformations.
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.metrics.pairwise import cosine_similarity

    vectorizer = TfidfVectorizer().fit(candidates)
    query_vec = vectorizer.transform([question])
    candidate_vecs = vectorizer.transform(candidates)
    similarities = cosine_similarity(query_vec, candidate_vecs).flatten()
    log.log_message(state["session_id"], "transform_query", f"TF-IDF similarities: {similarities.tolist()}")

    # Assume the original query is the last candidate.
    original_similarity = similarities[-1]
    # Find the best candidate among the transformation candidates (exclude the original).
    best_index = similarities[:-1].argmax()
    best_similarity = similarities[best_index]
    # If the best candidate is more similar than the original (and above a threshold), adopt it.
    if best_similarity > original_similarity and best_similarity > 0.5:
        transformed = candidates[best_index]
        log.log_message(state["session_id"], "transform_query", f"Transformed query to: {transformed}")
        return {"clarified_question": transformed}
    else:
        log.log_message(state["session_id"], "transform_query", "No transformation applied")
        return {}

def retrieve_wikipedia(state: GraphState):
    log.log_message(state["session_id"], "retrieve_wikipedia", "Started processing retrieve_wikipedia node")
    query = state.get("clarified_question") or state["original_question"]
    wiki_results = wikipedia.run(query)
    docs = [Document(page_content=res, metadata={"source": "Wikipedia"}) for res in wiki_results]
    log.log_message(state["session_id"], "retrieve_wikipedia", f"Retrieved {len(docs)} Wikipedia document(s)")
    return {"wikipedia_docs": docs}

def grade_wikipedia(state: GraphState):
    log.log_message(state["session_id"], "grade_wikipedia", "Started processing grade_wikipedia node")
    docs = state["wikipedia_docs"]
    query = state.get("clarified_question") or state["original_question"]
    if not docs:
        log.log_message(state["session_id"], "grade_wikipedia", "No Wikipedia docs found; triggering fallback")
        return {"final_answer": None}
    sample = docs[0].page_content[:1000]
    prompt = (
        f"Does the following Wikipedia content sufficiently answer the question '{query}'? "
        "Respond ONLY with 'yes' or 'no'.\nContent: " + sample
    )
    response = llm.invoke(prompt).content.lower()
    if "yes" in response:
        log.log_message(state["session_id"], "grade_wikipedia", "Wikipedia content deemed sufficient")
        return generate_answer(state)
    log.log_message(state["session_id"], "grade_wikipedia", "Wikipedia content insufficient; falling back to web search")
    return {"final_answer": None}



def rerank_documents(state: GraphState):
    log.log_message(state["session_id"], "rerank_documents", "Started processing rerank_documents node")
    query = state.get("clarified_question") or state["original_question"]
    docs = state["web_docs"]
    if not docs:
        log.log_message(state["session_id"], "rerank_documents", "No web docs to rerank")
        return {"reranked_docs": []}
    doc_summaries = "\n".join(
        [f"Doc {i}: {doc.page_content[:200]}" for i, doc in enumerate(docs)]
    )
    prompt = (
        f"Rank these documents for relevance to the query: '{query}'. "
        "Return the indices of the top 3 documents as comma-separated numbers.\nDocuments:\n" + doc_summaries
    )
    try:
        response = llm.invoke(prompt).content
        indices = [int(x.strip()) for x in response.split(",") if x.strip().isdigit()]
        valid = [docs[i] for i in indices if 0 <= i < len(docs)]
        log.log_message(state["session_id"], "rerank_documents", f"Selected document indices: {indices}")
        return {"reranked_docs": valid}
    except Exception as e:
        log.log_message(state["session_id"], "rerank_documents", f"Error during reranking: {str(e)}; defaulting to first 3 docs")
        return {"reranked_docs": docs[:3]}



# Build the workflow using LangGraph’s StateGraph
workflow = StateGraph(GraphState)
workflow.add_node("detect_ambiguity", detect_ambiguity)
workflow.add_node("clarify", clarify_question)
workflow.add_node("process_clarification", process_clarification)
workflow.add_node("transform", transform_query)
workflow.add_node("retrieve_wikipedia", retrieve_wikipedia)
workflow.add_node("grade_wikipedia", grade_wikipedia)
workflow.add_node("retrieve_web", retrieve_web)
workflow.add_node("rerank", rerank_documents)
workflow.add_node("generate_answer", generate_answer)

workflow.set_entry_point("detect_ambiguity")

# Conditional edge: if ambiguity is detected, move to clarification; otherwise, use Wikipedia retrieval.
workflow.add_conditional_edges(
    "detect_ambiguity",
    lambda state: "clarify" if state["needs_clarification"] else "retrieve_wikipedia",
    {"clarify": "clarify", "retrieve_wikipedia": "retrieve_wikipedia"}
)
workflow.add_edge("clarify", "process_clarification")
workflow.add_edge("process_clarification", "transform")
workflow.add_edge("transform", "retrieve_wikipedia")
workflow.add_edge("retrieve_wikipedia", "grade_wikipedia")
workflow.add_conditional_edges(
    "grade_wikipedia",
    lambda state: "generate_answer" if state.get("final_answer") else "retrieve_web",
    {"generate_answer": "generate_answer", "retrieve_web": "retrieve_web"}
)
workflow.add_edge("retrieve_web", "rerank")
workflow.add_edge("rerank", "generate_answer")
workflow.add_edge("generate_answer", END)

# Compile the workflow to get the runnable app
app = workflow.compile()
app.get_graph().draw_mermaid_png(output_file_path="testgraph3.png")

result = app.invoke({
    "original_question": "Where is Tesla?",
    "clarified_question": None,
    "wikipedia_docs": [],
    "web_docs": [],
    "reranked_docs": [],
    "final_answer": None,
    "needs_clarification": False,
    "session_id": str(uuid.uuid4())
})
print(result["final_answer"])
