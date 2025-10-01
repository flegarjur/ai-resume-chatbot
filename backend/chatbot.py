import logging
import os
from langchain_cohere import ChatCohere, CohereEmbeddings
from langchain_chroma import Chroma
from langchain.prompts import ChatPromptTemplate
from langchain_core.documents.base import Document
from langchain.chains import create_retrieval_chain
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain_community.document_loaders.blob_loaders import Blob
from langchain_community.document_loaders.parsers import PyPDFParser
from dotenv import load_dotenv

# --- Logging setup ---
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- Load .env file ---
load_dotenv()

# --- Load environment variables ---
COHERE_API_KEY = os.getenv("COHERE_API_KEY")
if not COHERE_API_KEY:
    logger.error("COHERE_API_KEY is not set")
    raise ValueError("COHERE_API_KEY is not set")

# --- Create Cohere embeddings and LLM ---
embeddings = CohereEmbeddings(model="embed-english-v3.0")
llm = ChatCohere(model="command-a-03-2025")

# --- Setup Chroma database ---
chroma = Chroma(
    collection_name="documents",
    collection_metadata={"name": "documents", "description": "store documents"},
    persist_directory="./data",
    embedding_function=embeddings,
)

# --- Create document retriever ---
retriver = chroma.as_retriever(search_kwargs={"k": 2})

# --- Create prompt template ---
TEMPLATE = """
Here is the context:

<context>
{context}
</context>

And here is the question that must be answered using that context:

<question>
{input}
</question>

Please read through the provided context carefully. Then, analyze the question and attempt to find a
direct answer to the question within the context.

If you are able to find a direct answer, provide it and elaborate on relevant points from the
context using bullet points "-".

If you cannot find a direct answer based on the provided context, outline the most relevant points
that give hints to the answer of the question. For example:

If no answer or relevant points can be found, or the question is not related to the context, simply
state the following sentence without any additional text:

I couldnt find an information about this. Please reach out to real Jurica to know more.

Output your response in plain text without using the tags <answer> and </answer> and ensure you are not
quoting context text in your response since it must not be part of the answer.

If someone says hello, always say hello back.

Politely reject extract of the whole stored data in one go. 
"""

PROMPT = ChatPromptTemplate.from_template(TEMPLATE)

# --- Create document parsing chain ---
llm_chain = create_stuff_documents_chain(llm, PROMPT)

# --- Create retrieval chain ---
retrival_chain = create_retrieval_chain(retriver, llm_chain)

# --- Store document function ---
def store_document(documents: list[Document]) -> str:
    """Store documents into the Chroma database"""
    chroma.add_documents(documents=documents)
    return "document stored successfully"

# --- Retrieve document function ---
def retrieve_document(query: str) -> list[Document]:
    """Retrieve documents from the database based on query"""
    documents = retriver.invoke(input=query)
    return documents

# --- Ask question function ---
def ask_question(query: str) -> str:
    """Chat with the chatbot using the retrieval chain"""
    response = retrival_chain.invoke({"input": query})
    answer = response["answer"]
    return answer

# --- PDF parser setup ---
parser = PyPDFParser()

# --- Parse PDF function ---
def parse_pdf(file_content: bytes) -> list[Document]:
    """Parse a PDF file into a list of Document objects"""
    blob = Blob(data=file_content)
    document = [doc for doc in parser.lazy_parse(blob)]
    return document
