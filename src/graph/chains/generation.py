from langchain import hub
from langchain_core.output_parsers import StrOutputParser
from langchain_openai import ChatOpenAI

llm = ChatOpenAI(temperature=0)
prompt = hub.pull("rlm/rag-prompt")
_template = """Given the following conversation and a follow up question, 
    rephrase the follow up question to be a standalone question,
    in its original language.
    Chat History:
    {chat_history}
    Follow Up Input: {question}
    Standalone question:"""

generation_chain = prompt | llm | StrOutputParser()
