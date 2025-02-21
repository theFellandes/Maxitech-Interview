from langchain_openai import ChatOpenAI

from logger.logger import CustomLogger
from src.graph.state import GraphState

llm = ChatOpenAI(model="gpt-4-turbo")


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
