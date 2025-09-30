from fastapi import FastAPI, UploadFile
from .chatbot import retrieve_document, store_document, parse_pdf, ask_question
from pydantic import BaseModel
from typing import List
import logging

# --- Logging setup ---
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- Create FastAPI app ---
app = FastAPI(
    title="Hello world! You are talking with RAG Chatbot.",
    description="A simple RAG chatbot API using Cohere embeddings and LLM.",
    version="0.1",
)

# --- Pydantic models ---
class DocumentResponse(BaseModel):
    """Model for document search response"""
    documents: List
    total: int
    query: str
    error: str = None

class DocumentUploadResponse(BaseModel):
    """Model for document upload response"""
    documents: List
    total: int
    status: str
    error: str = None

class AskResponse(BaseModel):
    """Model for chatbot ask response"""
    query: str
    answer: str
    error: str = None

# --- Root endpoint ---
@app.get("/")
def read_root():
    """Check service health"""
    return {
        "service": "RAG Chatbot using Cohere",
        "description": "Welcome to Chatbot RAG API",
        "status": "running",
    }

# --- Search documents endpoint ---
@app.get("/documents/{query}")
def search_documents(query: str) -> DocumentResponse:
    """Search stored documents based on query"""
    try:
        documents = retrieve_document(query)
        return {"documents": documents, "total": len(documents), "query": query}
    except Exception as e:
        logger.error(f"Error searching documents: {e}", exc_info=True)
        return {"error": str(e), "documents": [], "total": 0, "query": query}

# --- Upload documents endpoint ---
@app.post("/documents")
async def upload_documents(files: List[UploadFile]) -> DocumentUploadResponse:
    """Upload and store .pdf documents"""
    try:
        documents = []
        for file in files:
            # Only allow PDF files
            if file.content_type != "application/pdf":
                logger.error(f"Unsupported file type: {file.content_type}")
                raise ValueError("Only .pdf files are supported")
            content = await file.read()
            parsed_docs = parse_pdf(content)
            documents.extend(parsed_docs)
        status = store_document(documents)
        return {"documents": documents, "total": len(documents), "status": status}
    except Exception as e:
        logger.error(f"Error uploading documents: {e}", exc_info=True)
        return {"error": str(e), "status": "failed", "documents": [], "total": 0}

# --- Ask chatbot endpoint ---
@app.get("/ask")
def ask(query: str) -> AskResponse:
    """Submit a question to the chatbot"""
    try:
        answer = ask_question(query)
        return {"query": query, "answer": answer}
    except Exception as e:
        logger.error(f"Error asking question: {e}", exc_info=True)
        return {"error": str(e), "query": query, "answer": ""}
