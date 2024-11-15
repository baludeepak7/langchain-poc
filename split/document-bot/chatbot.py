
from langchain_ollama import ChatOllama
from langchain_core.prompts import ChatPromptTemplate
import chainlit as cl
from langchain_ollama import OllamaEmbeddings
from langchain.chains import create_retrieval_chain
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain.vectorstores import milvus

llm = ChatOllama(model="llama3.1",temperature=0)
embeddings = OllamaEmbeddings(
    model="llama3.1",
)
headers = {
    'Content-Type': 'application/json'
}

vectorstore = milvus.Milvus.from_documents(
    embedding=embeddings,
    collection_name="documentloaders",
    connection_args={"host":"100.29.185.236","port":19530}
)
retriever = vectorstore.as_retriever(search_kwargs={"k": 3})

system_prompt = (
    "Use the given context to answer the question. "
    "If you don't know the answer, say you don't know. "
    "Context: {context}"
)

prompt = ChatPromptTemplate.from_messages(
    [
        ("system", system_prompt),
        ("placeholder", "{chat_history}"),
        ("human", "{input}"),
        ("placeholder","{agent_scratchpad}"),
    ]
)

@cl.on_chat_start
def setup_multiple_chains():
    question_answer_chain = create_stuff_documents_chain(llm, prompt)
    chain = create_retrieval_chain(retriever, question_answer_chain)
    cl.user_session.set("chain", chain)



@cl.on_message
async def handle_message(message: cl.Message):
    user_message = message.content.lower()
    chain = cl.user_session.get("chain")
    response =  chain.invoke({"input":user_message})
    print(response['answer'])
    await cl.Message(response['answer']).send()
