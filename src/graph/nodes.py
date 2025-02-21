from dotenv import load_dotenv
load_dotenv()
from typing import Optional, List
from langchain_core.documents import Document
from langchain_openai import ChatOpenAI
from langchain_community.utilities import WikipediaAPIWrapper
from langchain_community.tools import TavilySearchResults
from logger.logger import CustomLogger
from src.graph.state import GraphState

# Initialize shared LLM and tool instances.
# TODO: Add doc comments to each function.
llm = ChatOpenAI(model="gpt-4-turbo")
wikipedia = WikipediaAPIWrapper(top_k_results=2)
web_search = TavilySearchResults(k=5)


def retrieve_web(state: GraphState) -> dict:
    CustomLogger.log_message(state["session_id"], "retrieve_web", "Started processing retrieve_web node")
    query = state.get("clarified_question") or state["original_question"]
    results = web_search.invoke(query)
    docs = [
        Document(page_content=res["content"], metadata={"source": res["url"]})
        for res in results
    ]
    CustomLogger.log_message(state["session_id"], "retrieve_web", f"Retrieved {len(docs)} web document(s)")
    return {"web_docs": docs}

def generate_answer(state: GraphState) -> dict:
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

def detect_ambiguity(state: GraphState) -> dict:
    CustomLogger.log_message(state["session_id"], "detect_ambiguity", "Started processing detect_ambiguity node")
    question = state["original_question"]
    prompt = f"Is the following question ambiguous? Respond ONLY with 'yes' or 'no'.\nQuestion: {question}"
    response = llm.invoke(prompt).content.lower()
    ambiguous = "yes" in response
    CustomLogger.log_message(state["session_id"], "detect_ambiguity", f"Ambiguity detected: {ambiguous}")
    return {"needs_clarification": ambiguous}

def clarify_question(state: GraphState) -> dict:
    CustomLogger.log_message(state["session_id"], "clarify_question", "Started processing clarify_question node")
    question = state["original_question"]
    prompt = (
        f'The user asked: "{question}"\n'
        "Generate a follow-up clarification question that asks the user to specify which interpretation they meant. "
        "Provide your answer as bullet points."
    )
    clarification = llm.invoke(prompt).content
    CustomLogger.log_message(state["session_id"], "clarify_question", f"Generated clarification: {clarification.strip()}")
    return {"clarified_question": clarification, "needs_clarification": True}

def process_clarification(state: GraphState) -> dict:
    CustomLogger.log_message(state["session_id"], "process_clarification", "Started processing process_clarification node")
    original = state["original_question"]
    clarification = state.get("clarified_question", "").strip()
    bullet_points = [line for line in clarification.split("\n") if line.strip().startswith("-")]
    if len(bullet_points) > 1:
        CustomLogger.log_message(state["session_id"], "process_clarification", "Clarification is too ambiguous; deferring to user input.")
        return {"clarified_question": clarification, "needs_clarification": True}
    else:
        prompt = (
            f'Original question: "{original}"\n'
            f'Clarification provided: "{clarification}"\n'
            "Based on this, provide a clarified version of the question that best captures the intended meaning. Keep it concise."
        )
        clarified = llm.invoke(prompt).content.strip()
        CustomLogger.log_message(state["session_id"], "process_clarification", f"Clarified question: {clarified}")
        return {"clarified_question": clarified, "needs_clarification": False}

def transform_query(state: GraphState) -> dict:
    CustomLogger.log_message(state["session_id"], "transform_query", "Started processing transform_query node")
    if state.get("needs_clarification", False):
        CustomLogger.log_message(state["session_id"], "transform_query", "Skipping transformation due to ambiguous clarification.")
        return {}
    question = state.get("clarified_question") or state["original_question"]
    candidates = [
        "Where is Tesla's main corporate headquarters located?",
        "Sequoia Capital investments 2025",
        question
    ]
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.metrics.pairwise import cosine_similarity
    vectorizer = TfidfVectorizer().fit(candidates)
    query_vec = vectorizer.transform([question])
    candidate_vecs = vectorizer.transform(candidates)
    similarities = cosine_similarity(query_vec, candidate_vecs).flatten()
    CustomLogger.log_message(state["session_id"], "transform_query", f"TF-IDF similarities: {similarities.tolist()}")
    original_similarity = similarities[-1]
    best_index = similarities[:-1].argmax()
    best_similarity = similarities[best_index]
    if best_similarity > original_similarity and best_similarity > 0.5:
        transformed = candidates[best_index]
        CustomLogger.log_message(state["session_id"], "transform_query", f"Transformed query to: {transformed}")
        return {"clarified_question": transformed}
    else:
        CustomLogger.log_message(state["session_id"], "transform_query", "No transformation applied")
        return {}

def retrieve_wikipedia(state: GraphState) -> dict:
    CustomLogger.log_message(state["session_id"], "retrieve_wikipedia", "Started processing retrieve_wikipedia node")
    query = state.get("clarified_question") or state["original_question"]
    wiki_results = wikipedia.run(query)
    docs = [Document(page_content=res, metadata={"source": "Wikipedia"}) for res in wiki_results]
    CustomLogger.log_message(state["session_id"], "retrieve_wikipedia", f"Retrieved {len(docs)} Wikipedia document(s)")
    return {"wikipedia_docs": docs}

def grade_wikipedia(state: GraphState) -> dict:
    CustomLogger.log_message(state["session_id"], "grade_wikipedia", "Started processing grade_wikipedia node")
    docs = state["wikipedia_docs"]
    query = state.get("clarified_question") or state["original_question"]
    if not docs:
        CustomLogger.log_message(state["session_id"], "grade_wikipedia", "No Wikipedia docs found; triggering fallback")
        return {"final_answer": None}
    sample = docs[0].page_content[:1000]
    prompt = f"Does the following Wikipedia content sufficiently answer the question '{query}'? Respond ONLY with 'yes' or 'no'.\nContent: {sample}"
    response = llm.invoke(prompt).content.lower()
    if "yes" in response:
        CustomLogger.log_message(state["session_id"], "grade_wikipedia", "Wikipedia content deemed sufficient")
        return generate_answer(state)
    CustomLogger.log_message(state["session_id"], "grade_wikipedia", "Wikipedia content insufficient; falling back to web search")
    return {"final_answer": None}

def rerank_documents(state: GraphState) -> dict:
    CustomLogger.log_message(state["session_id"], "rerank_documents", "Started processing rerank_documents node")
    query = state.get("clarified_question") or state["original_question"]
    docs = state["web_docs"]
    if not docs:
        CustomLogger.log_message(state["session_id"], "rerank_documents", "No web docs to rerank")
        return {"reranked_docs": []}
    doc_summaries = "\n".join([f"Doc {i}: {doc.page_content[:200]}" for i, doc in enumerate(docs)])
    prompt = (
        f"Rank these documents for relevance to the query: '{query}'. "
        "Return the indices of the top 3 documents as comma-separated numbers.\nDocuments:\n" + doc_summaries
    )
    try:
        response = llm.invoke(prompt).content
        indices = [int(x.strip()) for x in response.split(",") if x.strip().isdigit()]
        valid = [docs[i] for i in indices if 0 <= i < len(docs)]
        CustomLogger.log_message(state["session_id"], "rerank_documents", f"Selected document indices: {indices}")
        return {"reranked_docs": valid}
    except Exception as e:
        CustomLogger.log_message(state["session_id"], "rerank_documents", f"Error during reranking: {str(e)}; defaulting to first 3 docs")
        return {"reranked_docs": docs[:3]}
