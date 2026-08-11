import re
from models import FinancialStatement
from field_synonyms import FIELD_SYNONYMS


def clean_number(raw: str) -> float | None:
    """Convert a messy financial string like '$512,163' or '(1,646)' into a float."""
    if not raw:
        return None

    text = raw.strip()
    is_negative = text.startswith("(") and text.endswith(")")

    # keep only digits, dots, and minus signs
    cleaned = re.sub(r"[^\d.-]", "", text)
    if not cleaned:
        return None

    try:
        value = float(cleaned)
    except ValueError:
        return None

    return -value if is_negative else value


def extract_financial_data(table_rows: list[list[str]], statement: FinancialStatement = None) -> FinancialStatement:
    """Extract financial data from structured table rows (list of cell lists)."""
    if statement is None:
        statement = FinancialStatement()

    for row in table_rows:
        if not row or not row[0]:
            continue
        label = row[0].strip().lower()

        for field_name, synonyms in FIELD_SYNONYMS.items():
            if label in synonyms:
                # find the first cell in this row that looks numeric
                for cell in row[1:]:
                    number = clean_number(cell)
                    if number is not None:
                        setattr(statement, field_name, number)
                        break

    return statement


def extract_financial_data_from_text(page_text: str, statement: FinancialStatement = None) -> FinancialStatement:
    """Extract financial data from raw text lines (for PDFs without bordered tables).

    Handles lines like:
        Total assets $ 512,163 $ 411,976
        Operating income 109,433 88,523 83,383
        Net income $ 88,136 $ 72,361 $ 72,738
    """
    if statement is None:
        statement = FinancialStatement()

    for line in page_text.split("\n"):
        line_stripped = line.strip()
        if not line_stripped:
            continue

        line_lower = line_stripped.lower()

        for field_name, synonyms in FIELD_SYNONYMS.items():
            # Check if the line starts with (or matches) any synonym
            matched = False
            for synonym in synonyms:
                if line_lower.startswith(synonym):
                    matched = True
                    break

            if matched:
                # Extract all numbers from the remainder of the line
                # We want the FIRST numeric value (most recent year / primary column)
                numbers = re.findall(r"[\$\s]*\(?\d[\d,]*\.?\d*\)?", line_stripped)
                for num_str in numbers:
                    value = clean_number(num_str)
                    if value is not None:
                        setattr(statement, field_name, value)
                        break
                break  # don't match multiple synonyms on the same line

    return statement


if __name__ == "__main__":
    import pdfplumber

    with pdfplumber.open("test_data/sample_report.pdf") as pdf:
        page = pdf.pages[46]
        tables = page.extract_tables()
        all_rows = [row for table in tables for row in table]

    statement = extract_financial_data(all_rows)
    print(statement)