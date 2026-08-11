"""
Text chunker for RAG — splits narrative sections into overlapping chunks.
"""


def chunk_text(text: str, chunk_size: int = 500, overlap: int = 50) -> list[dict]:
    """Split text into overlapping chunks of approximately chunk_size words.
    
    Returns list of dicts with keys: text, chunk_index
    """
    words = text.split()
    chunks = []
    
    i = 0
    while i < len(words):
        chunk_words = words[i:i + chunk_size]
        chunk_text_str = " ".join(chunk_words)
        
        chunks.append({
            "text": chunk_text_str,
            "chunk_index": len(chunks),
        })
        
        # Advance by (chunk_size - overlap) words
        i += chunk_size - overlap
    
    return chunks
