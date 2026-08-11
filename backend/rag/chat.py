"""
RAG chat — answer questions grounded in report text.

Retrieves relevant chunks from the embedding store, then uses an LLM
to generate an answer citing specific source sections.
"""
import json
import logging
from typing import Optional

from config import get_settings

logger = logging.getLogger("finscope.rag.chat")


def answer_question(report_id: str, question: str) -> dict:
    """Answer a question about a report using RAG.
    
    Returns dict with keys: answer, sources
    """
    from rag.embed_store import query_chunks
    
    # Retrieve relevant chunks
    chunks = query_chunks(report_id, question, top_k=5)
    
    if not chunks:
        return {
            "answer": "I don't have enough context from this report to answer your question. The report's narrative sections may not have been indexed yet.",
            "sources": [],
        }
    
    # Build context from retrieved chunks
    context_parts = []
    for i, chunk in enumerate(chunks):
        context_parts.append(f"[Section {i+1}]\n{chunk['text']}")
    
    context = "\n\n".join(context_parts)
    
    # Use LLM to generate answer
    settings = get_settings()
    
    if not settings.anthropic_api_key:
        # Without LLM, return the raw chunks as a basic answer
        return {
            "answer": f"Based on the report, here are the most relevant sections:\n\n{context}",
            "sources": [{"chunk_index": c["chunk_index"], "text": c["text"][:200] + "..."} for c in chunks],
        }
    
    try:
        import anthropic
        client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
        
        response = client.messages.create(
            model="claude-sonnet-4-6-20250514",
            max_tokens=1024,
            system="""You are a financial analyst assistant. Answer questions about financial reports 
using ONLY the provided context. Cite which section(s) your answer comes from using [Section N] notation.
If the context doesn't contain enough information to answer, say so clearly.
Be concise and precise.""",
            messages=[{
                "role": "user",
                "content": f"Context from the report:\n\n{context}\n\nQuestion: {question}",
            }],
            temperature=0.1,
        )
        
        answer_text = response.content[0].text
        
        return {
            "answer": answer_text,
            "sources": [
                {
                    "chunk_index": c["chunk_index"],
                    "text": c["text"][:200] + ("..." if len(c["text"]) > 200 else ""),
                }
                for c in chunks
            ],
        }
        
    except Exception as e:
        logger.error("LLM answer generation failed: %s", e)
        return {
            "answer": f"I found relevant sections but couldn't generate a summary. Here are the key excerpts:\n\n{context[:1000]}",
            "sources": [{"chunk_index": c["chunk_index"], "text": c["text"][:200] + "..."} for c in chunks],
        }


def index_report_text(report_id: str, full_text: str):
    """Index all text from a report for RAG retrieval."""
    from rag.chunker import chunk_text
    from rag.embed_store import store_chunks
    
    chunks = chunk_text(full_text, chunk_size=500, overlap=50)
    
    if chunks:
        store_chunks(report_id, chunks)
        logger.info("Indexed %d chunks for report %s", len(chunks), report_id)
    else:
        logger.warning("No chunks generated for report %s", report_id)
