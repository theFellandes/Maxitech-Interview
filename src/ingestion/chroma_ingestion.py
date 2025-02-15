"""
This module contains the ChromaIngestion class, which is responsible
for loading and processing given data to vector database.
"""
import logging

from langchain.retrievers import SelfQueryRetriever

from src.ingestion.ingestion import Ingestion
from langchain_community.vectorstores import Chroma


class ChromaIngestion(Ingestion):
    def insert_documents(self, text_splits):
        """
        Embed the text splits using the specified embedding model and insert to vector database.
        """
        # Create the Chroma vectorstore
        vectorstore = Chroma.from_documents(
            documents=text_splits,
            collection_name="rag-chroma",
            embedding=self.embeddings,
            persist_directory="./.chroma",
        )
        logging.info("Chroma index is ready for retrieval!")
        return vectorstore.as_retriever()

    def retrieve_documents(self, query: str):
        """
        Retrieve documents related to the given query.
        """
        # Initialize the retriever
        retriever = Chroma(
            collection_name="rag-chroma",
            persist_directory="./.chroma",
            embedding_function=self.embeddings,
        ).as_retriever()
        return retriever.invoke(query)
