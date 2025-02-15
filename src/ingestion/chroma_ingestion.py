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
        vectorstore = Chroma.from_documents(text_splits, self.embeddings)
        logging.info("Chroma index is ready for retrieval!")
        return vectorstore.as_retriever()

    def retrieve_documents(self, query: str):
        """
        Retrieve documents related to the given query.
        """
        vectorstore = Chroma(
            embedding_function=self.embeddings,
        )

        # Initialize the retriever
        retriever = SelfQueryRetriever(vectorstore=vectorstore)
        return retriever.invoke(query)
