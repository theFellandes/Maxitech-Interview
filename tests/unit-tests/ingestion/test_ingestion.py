from ingestion.chroma_ingestion import ChromaIngestion
from dotenv import load_dotenv
load_dotenv()

from langchain_community.embeddings import OpenAIEmbeddings


def test_ingestion():
    chroma_ingestion = ChromaIngestion(embeddings=OpenAIEmbeddings())
    chroma_ingestion.load_docs()
    chroma_ingestion.insert_documents(chroma_ingestion.text_splitter())


if __name__ == '__main__':
    test_ingestion()
