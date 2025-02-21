import uuid
from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from dotenv import load_dotenv

load_dotenv()

from src.graph.graph import build_workflow

workflow = build_workflow()
chain_app = workflow.compile()

# In-memory chat history (for demo; use persistent storage in production)
chat_histories = {}

app = FastAPI(title="LangGraph Chat Bot API", version="1.0")
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

@app.get("/", response_class=HTMLResponse)
async def get_chat(request: Request, session_id: str = None):
    if not session_id:
        session_id = str(uuid.uuid4())
        chat_histories[session_id] = []
    history = chat_histories.get(session_id, [])
    return templates.TemplateResponse("index.html", {"request": request, "session_id": session_id, "history": history})

@app.post("/chat", response_class=JSONResponse)
async def post_chat_api(user_message: str = Form(...), session_id: str = Form(...)):
    # Process the user's message through your LangGraph chain
    state = {
        "chat_history": chat_histories.get(session_id, []),
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
    # Update chat history
    history = chat_histories.setdefault(session_id, [])
    history.append({"sender": "User", "message": user_message})
    bot_message = result.get("final_answer", "No answer generated.")
    history.append({"sender": "Bot", "message": bot_message})
    return JSONResponse(content={"bot_message": bot_message, "chat_history": history, "session_id": session_id})

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
