import logging
import threading
from pathlib import Path

from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

from config import CHROMA_DIR, has_env

log = logging.getLogger(__name__)

TEXT_SUFFIXES = {".txt", ".md", ".py", ".csv", ".json", ".js", ".ts", ".html", ".css", ".log", ".yaml", ".yml"}
SUPPORTED_SUFFIXES = {".pdf", ".docx"} | TEXT_SUFFIXES

_splitter = RecursiveCharacterTextSplitter(chunk_size=900, chunk_overlap=150)

_vectorstore = None
_vs_lock = threading.Lock()


def rag_available() -> bool:
    return has_env("GEMINI_API_KEY") or has_env("GOOGLE_API_KEY")


def get_vectorstore():
    """Create the embedding client + Chroma collection lazily.

    Building them at import time made the whole app crash on startup when the
    Gemini key was missing, and slowed down every cold start.
    """
    global _vectorstore
    if _vectorstore is None:
        with _vs_lock:
            if _vectorstore is None:
                if not rag_available():
                    raise RuntimeError("Document search needs GEMINI_API_KEY to be set.")
                from langchain_chroma import Chroma
                from langchain_google_genai import GoogleGenerativeAIEmbeddings

                _vectorstore = Chroma(
                    collection_name="agent_chatbot_docs",
                    embedding_function=GoogleGenerativeAIEmbeddings(model="gemini-embedding-001"),
                    persist_directory=str(CHROMA_DIR),
                )
    return _vectorstore


def read_file_text(file_path: str | Path) -> str:
    path = Path(file_path)
    suffix = path.suffix.lower()

    if suffix == ".pdf":
        from pypdf import PdfReader

        reader = PdfReader(str(path))
        return "\n".join((page.extract_text() or "") for page in reader.pages)

    if suffix == ".docx":
        import docx2txt

        return docx2txt.process(str(path))

    if suffix in TEXT_SUFFIXES:
        return path.read_text(encoding="utf-8", errors="ignore")

    raise ValueError("Unsupported file type.")


def add_document_to_rag(file_path: str | Path, thread_id: str, display_name: str | None = None) -> dict:
    text = read_file_text(file_path)
    if not text.strip():
        raise ValueError("No text could be extracted from this file (is it a scanned PDF?).")

    name = display_name or Path(file_path).name
    chunks = _splitter.split_text(text)
    docs = [
        Document(page_content=chunk, metadata={"thread_id": thread_id, "source": name, "chunk": i})
        for i, chunk in enumerate(chunks)
    ]
    get_vectorstore().add_documents(docs)
    return {"filename": name, "chunks": len(docs)}


def retrieve_from_rag(query: str, thread_id: str, k: int = 5) -> str:
    if not rag_available():
        return "Document search is not configured on this server."

    docs = get_vectorstore().similarity_search(query, k=k, filter={"thread_id": thread_id})
    if not docs:
        return "No uploaded documents found in this conversation."

    return "\n\n".join(
        f"[Source {i}: {doc.metadata.get('source', 'uploaded document')}]\n{doc.page_content}"
        for i, doc in enumerate(docs, start=1)
    )


def delete_thread_documents(thread_id: str) -> None:
    if not rag_available():
        return
    try:
        vs = get_vectorstore()
        ids = vs.get(where={"thread_id": thread_id}).get("ids", [])
        if ids:
            vs.delete(ids=ids)
    except Exception:  # never block a conversation delete on the vector store
        log.exception("Failed to delete vectors for thread %s", thread_id)
