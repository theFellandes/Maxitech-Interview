from dotenv import load_dotenv
load_dotenv()
from langgraph.graph import StateGraph, END
from src.graph.state import GraphState
import src.graph.nodes as nodes


def build_workflow() -> StateGraph:
    """
    Builds the workflow for the conversational agent.
    :return: The graph representing the workflow.
    """
    workflow = StateGraph(GraphState)
    workflow.add_node("detect_ambiguity", nodes.detect_ambiguity)
    workflow.add_node("clarify", nodes.clarify_question)
    workflow.add_node("process_clarification", nodes.process_clarification)
    workflow.add_node("transform", nodes.transform_query)
    workflow.add_node("retrieve_wikipedia", nodes.retrieve_wikipedia)
    workflow.add_node("grade_wikipedia", nodes.grade_wikipedia)
    workflow.add_node("retrieve_web", nodes.retrieve_web)
    workflow.add_node("rerank", nodes.rerank_documents)
    workflow.add_node("generate_answer", nodes.generate_answer)

    # Set the entry point for the conversation; initially, ambiguity is checked.
    workflow.set_entry_point("detect_ambiguity")

    # Define conditional edges:
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

    return workflow
