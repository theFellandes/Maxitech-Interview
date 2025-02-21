import uuid
from src.graph.graph import build_workflow
from dotenv import load_dotenv

def main():
    workflow = build_workflow()
    app = workflow.compile()
    # Define the initial state.
    state = {
        "original_question": "Where is Tesla?",
        "clarified_question": None,
        "wikipedia_docs": [],
        "web_docs": [],
        "reranked_docs": [],
        "final_answer": None,
        "needs_clarification": False,
        "session_id": str(uuid.uuid4())
    }
    result = app.invoke(state)
    print("Final Answer:", result.get("final_answer"))

if __name__ == "__main__":
    load_dotenv()
    main()
