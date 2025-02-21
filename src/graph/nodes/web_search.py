from langchain.schema import Document
from langchain_community.tools.tavily_search import TavilySearchResults

from src.graph.state import GraphState
from logger.logger import CustomLogger

web_search = TavilySearchResults(k=5)


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
