from dotenv import load_dotenv

load_dotenv()

from src.graph.graph import app

if __name__ == "__main__":
    print("Hello Advanced RAG")
    print(app.invoke(input={"question": "Where is Tesla?"}))
