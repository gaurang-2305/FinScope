STATEMENT_KEYWORDS = {
    "balance_sheet": [
        "Balance Sheet",
        "Statement of Financial Position",
        "Total Assets",
        "Total Liabilities",
        "Total Equity",
    ],
    "income_statement": [
        "Income Statement",
        "Statement of Profit and Loss",
        "Statement of Profit & Loss",
        "Total Revenue",
        "Net Profit",
    ],
    "cash_flow": [
        "Cash Flow Statement",
        "Cash Flows Statement",
        "Statement of Cash Flows",
        "Operating Activities",
        "Investing Activities",
        "Financing Activities",
    ],
}


def score_page(page_text: str, keywords: list[str]) -> int:
    score = 0
    page_text_lower = page_text.lower()
    for keyword in keywords:
        if keyword.lower() in page_text_lower:
            score += 1
    return score


def find_statement_page(pages_text: list[str], statement_type: str) -> int:
    keywords = STATEMENT_KEYWORDS[statement_type]
    best_score = 0
    best_page_index = -1

    for i, page_text in enumerate(pages_text):
        score = score_page(page_text, keywords)
        if score > best_score:
            best_score = score
            best_page_index = i

    return best_page_index


if __name__ == "__main__":
    from pdf_extractor import extract_text_pdfplumber

    pages = extract_text_pdfplumber("test_data/sample_report.pdf")

    bs_page = find_statement_page(pages, "balance_sheet")
    is_page = find_statement_page(pages, "income_statement")
    cf_page = find_statement_page(pages, "cash_flow")

    print(f"Balance Sheet likely at page: {bs_page + 1}")
    print(f"Income Statement likely at page: {is_page + 1}")
    print(f"Cash Flow Statement likely at page: {cf_page + 1}")