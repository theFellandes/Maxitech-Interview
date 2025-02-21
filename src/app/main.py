"""
Main module for FastAPI application.
"""

from fastapi import FastAPI

from src.app.dto.chat_request import ChatRequest
from src.ingestion.chroma_ingestion import ChromaIngestion
from dotenv import load_dotenv
load_dotenv()
from langchain_community.embeddings import OpenAIEmbeddings

# TODO: Add langserve ui
app = FastAPI()

ROOT = "/"
HEALTHCHECK = "/healthcheck"
CHAT = "/chat"


@app.get(ROOT)
def read_root():
    """
    Root endpoint returning a welcome message.
    """
    chroma_ingestion = ChromaIngestion(embeddings=OpenAIEmbeddings())
    print(chroma_ingestion.retrieve_documents("Gelir Vergisi Kanununa 5281"))
    return {"message": "Welcome to the FastAPI application"}


@app.get(HEALTHCHECK)
def read_root():
    """
    Health check endpoint returning a welcome message.
    """
    return {"message": "We are live!"}


@app.post(CHAT)
async def chat(chat_request: ChatRequest):
    """
    Endpoint to start a chat session with user.
    """
    return {"chat": chat_request.chat}
