"""
Text chunker for RAG — splits narrative sections into overlapping chunks.
"""


def chunk_text(text: str, chunk_size: int = 500, overlap: int = 50) -> list[dict]:
    """Split text into overlapping chunks of approximately chunk_size tokens.
    
    Uses word-level splitting as a simple tokenization proxy.
    
    Returns list of dicts with keys: text, start_char, end_char
    """
    words = text.split()
    chunks = []
    
    i = 0
    char_pos = 0
    
    while i < len(words):
        chunk_words = words[i:i + chunk_size]
        chunk_text = " ".join(chunk_words)
        
        # Track character positions for source mapping
        start_char = text.find(chunk_words[0], char_pos) if chunk_words else char_pos
        end_char = start_char + len(chunk_text)
        
        chunks.append({
            "text": chunk_text,
            "start_char": start_char,
            "end_char": end_char,
            "chunk_index": len(chunks),
        })
        
        i += chunk_size - overlap
        char_pos = max(start_char, char_pos)
    
    return chunks
