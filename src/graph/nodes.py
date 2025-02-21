"""
This module contains the node functions for the graph-based question answering system.
"""
from dotenv import load_dotenv
load_dotenv()
from langchain_core.documents import Document
from langchain_openai import ChatOpenAI
from langchain_community.utilities import WikipediaAPIWrapper
from langchain_community.tools import TavilySearchResults
from logger.logger import CustomLogger
from src.graph.state import GraphState


# Initialize shared LLM and tools
llm = ChatOpenAI(model="gpt-4-turbo")
wikipedia = WikipediaAPIWrapper(top_k_results=2)
web_search = TavilySearchResults(k=5)


def detect_ambiguity(state: GraphState) -> dict:
    """
    Detects ambiguity in the user's question.
    :param state: The current state of the graph
    :return: The updated state with the ambiguity status
    """
    CustomLogger.log_message(state["session_id"], "detect_ambiguity", "Started processing detect_ambiguity node")
    # Convert each chat history entry (a dict) into a string
    conversation = "\n".join([f"{msg['sender']}: {msg['message']}" for msg in state.get("chat_history", [])])
    prompt = (
        f"Based on the conversation history below:\n{conversation}\n\n"
        f"Is the current question ambiguous? Respond ONLY with 'yes' or 'no'.\n"
        f"Current question: {state['original_question']}"
    )
    response = llm.invoke(prompt).content.lower()
    ambiguous = "yes" in response
    CustomLogger.log_message(state["session_id"], "detect_ambiguity", f"Ambiguity detected: {ambiguous}")
    return {"needs_clarification": ambiguous}


def clarify_question(state: GraphState) -> dict:
    """
    Generates a clarification question to resolve ambiguity.
    :param state: The current state of the graph
    :return: Clarification question and flag indicating need for clarification
    """
    CustomLogger.log_message(state["session_id"], "clarify_question", "Started processing clarify_question node")
    # Convert each history entry (a dict) to a string format
    conversation = "\n".join([f"{msg['sender']}: {msg['message']}" for msg in state.get("chat_history", [])])
    prompt = (
        f"Conversation so far:\n{conversation}\n\n"
        f"The user originally asked: \"{state['original_question']}\"\n"
        "Generate a follow-up clarification question in bullet points asking the user to specify their intent."
    )
    clarification = llm.invoke(prompt).content
    CustomLogger.log_message(state["session_id"], "clarify_question", f"Generated clarification: {clarification.strip()}")
    return {"clarified_question": clarification, "needs_clarification": True}


def process_clarification(state: GraphState) -> dict:
    """
    Processes the clarification question to determine if it is specific enough.
    :param state: The current state of the graph
    :return: Clarified question and flag indicating need for further clarification
    """
    CustomLogger.log_message(state["session_id"], "process_clarification", "Started processing process_clarification node")
    original = state["original_question"]
    clarification = state.get("clarified_question", "").strip()
    # Convert chat history entries (dicts) into strings
    conversation = "\n".join(
        [f"{msg['sender']}: {msg['message']}" for msg in state.get("chat_history", [])]
    )
    # Check if clarification is too ambiguous: if it contains more than one bullet point, defer to user input
    bullet_points = [line for line in clarification.split("\n") if line.strip().startswith("-")]
    if len(bullet_points) > 1:
        CustomLogger.log_message(state["session_id"], "process_clarification", "Clarification is too ambiguous; deferring to user input.")
        return {"clarified_question": clarification, "needs_clarification": True}
    else:
        prompt = (
            f"Conversation history:\n{conversation}\n\n"
            f"Original question: \"{original}\"\n"
            f"Clarification provided: \"{clarification}\"\n"
            "Based on this, provide a clarified version of the question that best captures the intended meaning. Keep it concise."
        )
        clarified = llm.invoke(prompt).content.strip()
        CustomLogger.log_message(state["session_id"], "process_clarification", f"Clarified question: {clarified}")
        return {"clarified_question": clarified, "needs_clarification": False}


def transform_query(state: GraphState) -> dict:
    """
    Transforms the query for better clarity.
    :param state: The current state of the graph
    :return: Optimized query if transformation is successful
    """
    CustomLogger.log_message(state["session_id"], "transform_query", "Started processing transform_query node")
    if state.get("needs_clarification", False):
        CustomLogger.log_message(state["session_id"], "transform_query", "Skipping transformation due to ambiguous clarification.")
        return {}
    # Use history to possibly refine the question further
    conversation = "\n".join(state["chat_history"]) if state["chat_history"] else ""
    question = state.get("clarified_question") or state["original_question"]
    prompt = (
        f"Conversation so far:\n{conversation}\n\n"
        f"Refine the following query for clarity based on the conversation: '{question}'"
    )
    transformed = llm.invoke(prompt).content.strip()
    if transformed and transformed.lower() != question.lower():
        CustomLogger.log_message(state["session_id"], "transform_query", f"Transformed query to: {transformed}")
        return {"clarified_question": transformed}
    else:
        CustomLogger.log_message(state["session_id"], "transform_query", "No transformation applied")
        return {}


def retrieve_wikipedia(state: GraphState) -> dict:
    """
    Retrieves relevant Wikipedia content for the query.
    :param state: The current state of the graph
    :return: Retrieved Wikipedia documents
    """
    CustomLogger.log_message(state["session_id"], "retrieve_wikipedia", "Started processing retrieve_wikipedia node")
    # Convert chat history from dicts to strings
    conversation = "\n".join([f"{msg['sender']}: {msg['message']}" for msg in state.get("chat_history", [])])
    query = state.get("clarified_question") or state["original_question"]
    prompt = (
        f"Conversation history:\n{conversation}\n\n"
        f"Retrieve relevant Wikipedia content for the query: '{query}'."
    )
    wiki_results = wikipedia.run(prompt)
    docs = [Document(page_content=res, metadata={"source": "Wikipedia"}) for res in wiki_results]
    CustomLogger.log_message(state["session_id"], "retrieve_wikipedia", f"Retrieved {len(docs)} Wikipedia document(s)")
    return {"wikipedia_docs": docs}


def grade_wikipedia(state: GraphState) -> dict:
    """
    Grades the Wikipedia content to determine if it sufficiently answers the query.
    :param state: The current state of the graph
    :return: Generated answer if Wikipedia content is sufficient
    """
    CustomLogger.log_message(state["session_id"], "grade_wikipedia", "Started processing grade_wikipedia node")
    docs = state["wikipedia_docs"]
    # Convert chat history entries to strings
    conversation = "\n".join(
        [f"{msg['sender']}: {msg['message']}" for msg in state.get("chat_history", [])]
    )
    query = state.get("clarified_question") or state["original_question"]
    if not docs:
        CustomLogger.log_message(state["session_id"], "grade_wikipedia", "No Wikipedia docs found; triggering fallback")
        return {"final_answer": None}
    sample = docs[0].page_content[:1000]
    prompt = (
        f"Conversation history:\n{conversation}\n\n"
        f"Does the following Wikipedia content sufficiently answer the query '{query}'? "
        "Respond ONLY with 'yes' or 'no'.\nContent: " + sample
    )
    response = llm.invoke(prompt).content.lower()
    if "yes" in response:
        CustomLogger.log_message(state["session_id"], "grade_wikipedia", "Wikipedia content deemed sufficient")
        return generate_answer(state)
    CustomLogger.log_message(state["session_id"], "grade_wikipedia", "Wikipedia content insufficient; falling back to web search")
    return {"final_answer": None}


def retrieve_web(state: GraphState) -> dict:
    """
    Retrieves relevant web content for the query.
    :param state: The current state of the graph
    :return: Uses Tavily to retrieve web documents
    """
    CustomLogger.log_message(state["session_id"], "retrieve_web", "Started processing retrieve_web node")
    # Convert each history entry (a dict) to a string: "Sender: Message"
    conversation = "\n".join(
        [f"{msg.get('sender', 'Unknown')}: {msg.get('message', '')}" for msg in state.get("chat_history", [])]
    )
    query = state.get("clarified_question") or state["original_question"]
    prompt = (
        f"Conversation history:\n{conversation}\n\n"
        f"Perform a web search for: '{query}' and return the top results."
    )
    results = web_search.invoke(prompt)
    docs = []
    for res in results:
        if isinstance(res, dict):
            content = res.get("content", "")
            source = res.get("url", "unknown")
        else:
            content = res
            source = "unknown"
        docs.append(Document(page_content=content, metadata={"source": source}))
    CustomLogger.log_message(state["session_id"], "retrieve_web", f"Retrieved {len(docs)} web document(s)")
    return {"web_docs": docs}


def rerank_documents(state: GraphState) -> dict:
    """
    Reranks the web documents based on relevance.
    :param state: The current state of the graph
    :return: Performs reranking of web documents
    """
    CustomLogger.log_message(state["session_id"], "rerank_documents", "Started processing rerank_documents node")
    query = state.get("clarified_question") or state["original_question"]
    docs = state["web_docs"]
    if not docs:
        CustomLogger.log_message(state["session_id"], "rerank_documents", "No web docs to rerank")
        return {"reranked_docs": []}

    # Convert chat history entries (dicts) to strings
    conversation = "\n".join(
        [f"{msg.get('sender', 'Unknown')}: {msg.get('message', '')}" for msg in state.get("chat_history", [])]
    )
    doc_summaries = "\n".join([f"Doc {i}: {doc.page_content[:200]}" for i, doc in enumerate(docs)])

    prompt = (
            f"Conversation history:\n{conversation}\n\n"
            f"Based on the conversation history and the query '{query}', rank these documents by relevance. "
            "Return the indices of the top 3 documents as comma-separated numbers.\nDocuments:\n" + doc_summaries
    )

    try:
        response = llm.invoke(prompt).content
        indices = [int(x.strip()) for x in response.split(",") if x.strip().isdigit()]
        valid = [docs[i] for i in indices if 0 <= i < len(docs)]
        CustomLogger.log_message(state["session_id"], "rerank_documents", f"Selected document indices: {indices}")
        return {"reranked_docs": valid}
    except Exception as e:
        CustomLogger.log_message(state["session_id"], "rerank_documents",
                                 f"Error during reranking: {str(e)}; defaulting to first 3 docs")
        return {"reranked_docs": docs[:3]}


def generate_answer(state: GraphState) -> dict:
    """
    Generates a concise answer based on the conversation history and retrieved documents.
    :param state: The current state of the graph
    :return: Generated answer
    """
    CustomLogger.log_message(state["session_id"], "generate_answer", "Started processing generate_answer node")
    # Convert each entry in chat_history to a string format.
    conversation = "\n".join(
        [f"{msg.get('sender', 'Unknown')}: {msg.get('message', '')}" for msg in state.get("chat_history", [])]
    ) if state.get("chat_history") else ""

    query = state.get("clarified_question") or state["original_question"]

    if state["wikipedia_docs"]:
        source = "Wikipedia"
        content = "\n".join([d.page_content[:500] for d in state["wikipedia_docs"]])
    else:
        source = "Web"
        content = "\n".join([d.page_content[:500] for d in state["reranked_docs"]])

    prompt = (
        f"Conversation history:\n{conversation}\n\n"
        f"Generate a concise 1-2 sentence answer for the query: '{query}'. "
        f"Use the following content from {source}:\n{content}\n"
        "Include the source in parentheses at the end."
    )

    answer = llm.invoke(prompt).content.strip()
    CustomLogger.log_message(state["session_id"], "generate_answer", f"Generated answer: {answer}")
    return {"final_answer": answer}
