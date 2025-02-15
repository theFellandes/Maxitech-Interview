"""
This module contains the Ingestion class, which is responsible for loading and processing given data to vector database.
This is an abstract class that should be inherited by the specific ingestion classes.
"""
import os
import logging

from langchain_core.embeddings import Embeddings
from pydantic import BaseModel
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import PyPDFLoader
from langchain_core.documents.base import Document


class Ingestion(BaseModel):

    docs_list: list = []
    embeddings: Embeddings = None

    model_config = {
        'arbitrary_types_allowed': True,
    }

    def load_docs(self):
        """
        Load and process PDF documents.
        """
        # Define the path to the folder containing PDF files
        documents_folder = "./documents"
        pdf_files = [
            os.path.join(documents_folder, file)
            for file in os.listdir(documents_folder)
            if file.endswith(".pdf")
        ]

        # Load and process PDF documents
        logging.info("Loading and processing PDF documents...")
        docs = [PyPDFLoader(pdf).load() for pdf in pdf_files]
        self.docs_list = [item for sublist in docs for item in sublist]
        logging.info(f"Number of documents loaded: {len(self.docs_list)}")

    def text_splitter(self, chunk_size: int = 250, chunk_overlap: int = 0) -> list[Document]:
        """
        Split the documents into manageable chunks using the RecursiveCharacterTextSplitter.
        """
        logging.info("Splitting the documents into manageable chunks...")
        text_splitter = RecursiveCharacterTextSplitter.from_tiktoken_encoder(
            chunk_size=chunk_size, chunk_overlap=chunk_overlap
        )
        logging.info("Splitting documents...")
        return text_splitter.split_documents(self.docs_list)

    def insert_documents(self, text_splits):
        """
        Embed the text splits using the specified embedding model and insert to vector database.
        """
        raise NotImplementedError
