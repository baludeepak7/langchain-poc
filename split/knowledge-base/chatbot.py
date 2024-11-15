
from langchain_ollama import ChatOllama
from langchain_ollama import OllamaEmbeddings
from langchain_community.document_loaders import PyPDFLoader,TextLoader,Docx2txtLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
import os
from langchain.vectorstores import milvus

llm = ChatOllama(model="llama3.1",temperature=0)
embeddings = OllamaEmbeddings(
    model="llama3.1",
)
headers = {
    'Content-Type': 'application/json'
}

documents = []
for file in os.listdir('docs'):
    if file.endswith('.pdf'):
        pdf_path = './docs/' + file
        loader = PyPDFLoader(pdf_path)
        documents.extend(loader.load())
    elif file.endswith('.docx') or file.endswith('.doc'):
        doc_path = './docs/' + file
        loader = Docx2txtLoader(doc_path)
        documents.extend(loader.load())
    elif file.endswith('.txt'):
        text_path = './docs/' + file
        loader = TextLoader(text_path)
        documents.extend(loader.load())
        

text_splitter = RecursiveCharacterTextSplitter(chunk_size=1500, chunk_overlap=0)
all_splits = text_splitter.split_documents(documents)
milvus.Milvus.from_documents(
    documents=all_splits,
    embedding=embeddings,
    collection_name="documentloaders",
    connection_args={"host":"100.29.185.236","port":19530}
)
print(all_splits)