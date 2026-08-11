"""
OCR fallback for scanned PDFs.

When has_extractable_text() returns False, render pages to images
and OCR them to get text for the downstream pipeline.
"""
import io
import logging
from typing import Optional

logger = logging.getLogger("finscope.ocr")


def ocr_pdf_pages(pdf_path: str) -> list[str]:
    """Render PDF pages to images and OCR them.
    
    Returns a list of strings, one per page (same format as extract_text_pdfplumber).
    """
    try:
        import fitz  # PyMuPDF
    except ImportError:
        logger.error("PyMuPDF not installed — cannot render pages for OCR")
        return []

    pages_text = []
    doc = fitz.open(pdf_path)

    for page_num in range(len(doc)):
        page = doc[page_num]
        
        # Render page to image at 300 DPI for good OCR quality
        mat = fitz.Matrix(300 / 72, 300 / 72)
        pix = page.get_pixmap(matrix=mat)
        img_bytes = pix.tobytes("png")

        text = _ocr_image(img_bytes)
        pages_text.append(text)
        
        if page_num % 10 == 0:
            logger.info("OCR progress: page %d/%d", page_num + 1, len(doc))

    doc.close()
    logger.info("OCR complete: %d pages processed", len(pages_text))
    return pages_text


def _ocr_image(img_bytes: bytes) -> str:
    """OCR a single image. Tries pytesseract first, falls back to basic extraction."""
    # Try pytesseract
    try:
        import pytesseract
        from PIL import Image
        
        image = Image.open(io.BytesIO(img_bytes))
        text = pytesseract.image_to_string(image)
        return text
    except ImportError:
        logger.warning("pytesseract not installed — OCR unavailable")
        return ""
    except Exception as e:
        logger.warning("pytesseract failed: %s", e)
        return ""
