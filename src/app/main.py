"""
Main module for FastAPI application.
"""

from fastapi import FastAPI

from src.ingestion.chroma_ingestion import ChromaIngestion
from langchain_community.embeddings import OpenAIEmbeddings

app = FastAPI()


@app.get("/")
def read_root():
    """
    Root endpoint returning a welcome message.
    """
    chroma_ingestion = ChromaIngestion(embeddings=OpenAIEmbeddings())
    print(chroma_ingestion.retrieve_documents("Gelir Vergisi Kanununa 5281"))
    return {"message": "Welcome to the FastAPI application"}


@app.get("/items/{item_id}")
def read_item(item_id: int, q: str = None):
    """
    Endpoint to get an item by ID.

    Parameters:
    - item_id (int): ID of the item
    - q (str, optional): Query parameter

    Returns:
    - dict: Item details
    """
    return {"item_id": item_id, "q": q}
