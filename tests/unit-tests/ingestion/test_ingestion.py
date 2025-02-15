from src.ingestion.chroma_ingestion import ChromaIngestion
from dotenv import load_dotenv
load_dotenv()

from langchain_community.embeddings import OpenAIEmbeddings
from logger.logger import CustomLogger

console_logger = CustomLogger(handler_type='console')


@console_logger
def test_ingestion():
    chroma_ingestion = ChromaIngestion(embeddings=OpenAIEmbeddings())
    chroma_ingestion.load_docs()
    retriever = chroma_ingestion.insert_documents(chroma_ingestion.text_splitter())
    print(retriever.invoke("Gelir Vergisi Kanununa 5281"))


if __name__ == '__main__':
    test_ingestion()
