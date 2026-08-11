"""
Embedding store for RAG — embeds text chunks and stores in ChromaDB.
"""
import logging
from typing import Optional

logger = logging.getLogger("finscope.rag")

_collection = None


def _get_collection():
    """Lazy-initialize ChromaDB collection."""
    global _collection
    if _collection is not None:
        return _collection
    
    try:
        import chromadb
        client = chromadb.Client()  # In-memory for now; Phase 9 configures persistence
        _collection = client.get_or_create_collection(
            name="finscope_chunks",
            metadata={"hnsw:space": "cosine"},
        )
        logger.info("ChromaDB collection initialized")
        return _collection
    except ImportError:
        logger.error("chromadb not installed — RAG unavailable")
        raise


def store_chunks(report_id: str, chunks: list[dict]):
    """Embed and store text chunks for a report."""
    collection = _get_collection()
    
    # Remove any existing chunks for this report
    try:
        existing = collection.get(where={"report_id": report_id})
        if existing and existing["ids"]:
            collection.delete(ids=existing["ids"])
    except Exception:
        pass  # Collection might be empty
    
    ids = [f"{report_id}_chunk_{c['chunk_index']}" for c in chunks]
    documents = [c["text"] for c in chunks]
    metadatas = [{"report_id": report_id, "chunk_index": c["chunk_index"]} for c in chunks]
    
    # ChromaDB will use its default embedding function
    collection.add(
        ids=ids,
        documents=documents,
        metadatas=metadatas,
    )
    
    logger.info("Stored %d chunks for report %s", len(chunks), report_id)


def query_chunks(report_id: str, question: str, top_k: int = 5) -> list[dict]:
    """Retrieve the most relevant chunks for a question about a specific report."""
    collection = _get_collection()
    
    results = collection.query(
        query_texts=[question],
        n_results=top_k,
        where={"report_id": report_id},
    )
    
    chunks = []
    if results and results["documents"]:
        for i, doc in enumerate(results["documents"][0]):
            chunks.append({
                "text": doc,
                "chunk_index": results["metadatas"][0][i].get("chunk_index", i) if results["metadatas"] else i,
                "distance": results["distances"][0][i] if results.get("distances") else None,
            })
    
    return chunks
