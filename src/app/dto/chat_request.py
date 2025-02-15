"""This module contains the DTO for the chat request."""
from pydantic import BaseModel


class ChatRequest(BaseModel):
    # TODO: Will add ULID for the persistent chat
    chat: str
