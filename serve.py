import uuid
from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from dotenv import load_dotenv

load_dotenv()

# Import your modular chain builder
from src.graph.graph import build_workflow

# Build and compile the LangGraph workflow (chain)
workflow = build_workflow()
chain_app = workflow.compile()

# In-memory store for chat history (for demonstration purposes)
chat_histories = {}

# Initialize FastAPI and Jinja2 templates
app = FastAPI(
    title="LangGraph Chat Bot API",
    description="A simple chat bot API using FastAPI and LangGraph",
    version="1.0",
)
templates = Jinja2Templates(directory="templates")


def process_message(session_id: str, user_message: str) -> dict:
    """
    Helper function to invoke the chain.
    For simplicity, we treat the incoming message as the new original question.
    """
    state = {
        "original_question": user_message,
        "clarified_question": None,
        "wikipedia_docs": [],
        "web_docs": [],
        "reranked_docs": [],
        "final_answer": None,
        "needs_clarification": False,
        "session_id": session_id,
    }
    result = chain_app.invoke(state)
    return result


@app.get("/", response_class=HTMLResponse)
async def get_chat(request: Request, session_id: str = None):
    """
    Render the chat UI.
    If no session_id is provided, generate one and initialize empty chat history.
    """
    if not session_id:
        session_id = str(uuid.uuid4())
        chat_histories[session_id] = []
    history = chat_histories.get(session_id, [])
    return templates.TemplateResponse("index.html", {"request": request, "session_id": session_id, "history": history})


@app.post("/chat", response_class=RedirectResponse)
async def post_chat(request: Request, user_message: str = Form(...), session_id: str = Form(...)):
    """
    Handle incoming chat messages.
    Process the user's message via the chain, update the chat history, and redirect back to the UI.
    """
    result = process_message(session_id, user_message)
    answer = result.get("final_answer", "No answer generated.")

    # Append the new messages to the chat history
    if session_id not in chat_histories:
        chat_histories[session_id] = []
    chat_histories[session_id].append({"sender": "User", "message": user_message})
    chat_histories[session_id].append({"sender": "Bot", "message": answer})

    # Redirect to the chat UI preserving the session_id
    return RedirectResponse(url=f"/?session_id={session_id}", status_code=303)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
