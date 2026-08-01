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


def extract_balance_sheet(table_rows: list[list[str]]) -> FinancialStatement:
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


if __name__ == "__main__":
    import pdfplumber

    with pdfplumber.open("test_data/sample_report.pdf") as pdf:
        page = pdf.pages[46]
        tables = page.extract_tables()
        all_rows = [row for table in tables for row in table]

    statement = extract_balance_sheet(all_rows)
    print(statement)