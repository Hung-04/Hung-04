import chromadb
from sentence_transformers import SentenceTransformer
import random
import os
import torch

MODEL_NAME = "paraphrase-multilingual-mpnet-base-v2"
CHROMA_PATH = "./chroma_db"

# Khởi tạo một lần duy nhất khi import
_model = None
_client = None


def get_model() -> SentenceTransformer:
    global _model
    if _model is None:
        # Tự động phát hiện GPU nếu có để tăng tốc embedding
        device = "cuda" if torch.cuda.is_available() else "cpu"
        print(f"DEBUG: Loading embedding model on {device.upper()}")
        _model = SentenceTransformer(MODEL_NAME, device=device)
        if device == "cuda":
            print(f"DEBUG: GPU detected - {torch.cuda.get_device_name(0)}")
    return _model


def get_client() -> chromadb.PersistentClient:
    global _client
    if _client is None:
        os.makedirs(CHROMA_PATH, exist_ok=True)
        _client = chromadb.PersistentClient(path=CHROMA_PATH)
    return _client


def index_chunks(doc_id: str, chunks: list[str]) -> None:
    model = get_model()
    client = get_client()
    collection = client.get_or_create_collection(name="documents")

    embeddings = model.encode(chunks, show_progress_bar=False).tolist()
    ids = [f"{doc_id}_chunk_{i}" for i in range(len(chunks))]
    metadatas = [{"doc_id": doc_id, "chunk_index": i} for i in range(len(chunks))]

    # Upsert để tránh lỗi nếu chạy lại với cùng doc_id
    collection.upsert(
        documents=chunks,
        embeddings=embeddings,
        ids=ids,
        metadatas=metadatas,
    )


def get_chunks_by_doc(doc_id: str, sample_size: int = 10) -> list[str]:
    model = get_model()
    client = get_client()

    try:
        collection = client.get_collection("documents")
    except Exception:
        return []
    query_embedding = model.encode(
        ["sinh câu hỏi từ nội dung tài liệu"],
        show_progress_bar=False
    ).tolist()

    results = collection.query(
        query_embeddings=query_embedding,
        n_results=sample_size,
        where={"doc_id": doc_id}
    )

    return results["documents"][0] if results["documents"] else []


def delete_chunks_by_doc(doc_id: str) -> None:
    """Xóa toàn bộ chunks của tài liệu khỏi ChromaDB."""
    client = get_client()
    try:
        collection = client.get_collection("documents")
        collection.delete(where={"doc_id": doc_id})
    except Exception:
        pass