import time
import pdfplumber
import fitz  # PyMuPDF


def extract_text_pdfplumber(pdf_path: str) -> list[str]:
    """Extract text from a PDF, one string per page, using pdfplumber."""
    pages_text = []
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            text = page.extract_text() or ""
            pages_text.append(text)
    return pages_text


def extract_text_pymupdf(pdf_path: str) -> list[str]:
    """Extract text from a PDF, one string per page, using PyMuPDF."""
    pages_text = []
    doc = fitz.open(pdf_path)
    for page in doc:
        pages_text.append(page.get_text())
    doc.close()
    return pages_text


def has_extractable_text(pages_text: list[str]) -> bool:
    """Rough check for whether a PDF actually has a text layer,
    or is likely a scanned image with nothing extractable."""
    total_chars = sum(len(p.strip()) for p in pages_text)
    return total_chars > 100


if __name__ == "__main__":
    pdf_path = "test_data/sample_report.pdf"

    start = time.time()
    plumber_pages = extract_text_pdfplumber(pdf_path)
    plumber_time = time.time() - start

    start = time.time()
    mupdf_pages = extract_text_pymupdf(pdf_path)
    mupdf_time = time.time() - start

    print(f"pdfplumber: {len(plumber_pages)} pages, {plumber_time:.2f}s")
    print(f"PyMuPDF:    {len(mupdf_pages)} pages, {mupdf_time:.2f}s")

    # print("\n--- pdfplumber page 1 (first 500 chars) ---")
    # print(plumber_pages[0][:500])

    # print("\n--- PyMuPDF page 1 (first 500 chars) ---")
    # print(mupdf_pages[0][:500])

    BALANCE_SHEET_PAGE = 46  # change this to your actual page index

    print(f"\n--- pdfplumber page {BALANCE_SHEET_PAGE + 1} (Balance Sheet) ---")
    print(plumber_pages[BALANCE_SHEET_PAGE][:1500])

    print(f"\n--- PyMuPDF page {BALANCE_SHEET_PAGE + 1} (Balance Sheet) ---")
    print(mupdf_pages[BALANCE_SHEET_PAGE][:1500])

    print("\nHas extractable text (pdfplumber):", has_extractable_text(plumber_pages))

    