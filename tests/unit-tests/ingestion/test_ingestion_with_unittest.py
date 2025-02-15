import unittest
from dotenv import load_dotenv
load_dotenv()
from langchain_community.embeddings import OpenAIEmbeddings
from src.ingestion.chroma_ingestion import ChromaIngestion
from langchain_core.documents.base import Document


class TestChromaIngestion(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Initialize ChromaIngestion with OpenAIEmbeddings
        cls.chroma_ingestion = ChromaIngestion(embeddings=OpenAIEmbeddings())

    def test_load_docs(self):
        # Test the load_docs method
        self.chroma_ingestion.load_docs()
        self.assertGreater(len(self.chroma_ingestion.docs_list), 0, "No documents loaded")

    def test_text_splitter(self):
        # Ensure documents are loaded first
        self.chroma_ingestion.load_docs()
        # Test the text_splitter method
        text_splits = self.chroma_ingestion.text_splitter()
        self.assertGreater(len(text_splits), 0, "Text splitting failed")

    def test_insert_documents(self):
        # Ensure documents are loaded and split first
        self.chroma_ingestion.load_docs()
        text_splits = self.chroma_ingestion.text_splitter()
        # Test the insert_documents method
        retriever = self.chroma_ingestion.insert_documents(text_splits)
        self.assertIsNotNone(retriever, "Retriever is None")
        # Test the retriever's invoke method
        result = retriever.invoke("Gelir Vergisi Kanununa 5281")
        self.assertIsInstance(result, list, "Result is not a list")
        self.assertGreater(len(result), 0, "No documents retrieved")
        self.assertIsInstance(result[0], Document, "Retrieved item is not a Document")


if __name__ == '__main__':
    unittest.main()
