"""
FinScope extraction pipeline.

Flow:
  1. PDF → text extraction → page classification
  2. Stage 1: regex/synonym extraction (fast, free)
  3. Stage 2: LLM fallback for fields still None (if API key configured)
  4. Accounting-identity validation → re-extract on failure
  5. Return ExtractionResult with provenance per field
"""
import logging
import pdfplumber

from pdf_extractor import extract_text_pdfplumber, has_extractable_text
from statement_classifier import find_statement_page
from statement_extractor import extract_financial_data, extract_financial_data_from_text
from models import FinancialStatement, FieldProvenance, ExtractionResult
from validators import validate_statement

logger = logging.getLogger("finscope.pipeline")


def _extract_from_page(
    pdf_page,
    page_text: str,
    page_idx: int,
    statement: FinancialStatement,
    provenance: dict,
) -> FinancialStatement:
    """Try table-based extraction first; fall back to text-based extraction.
    Populates provenance for each newly extracted field."""

    # Snapshot which fields are already populated
    before = {k: v for k, v in statement.model_dump().items() if v is not None}

    tables = pdf_page.extract_tables()
    if tables:
        rows = [row for table in tables for row in table]
        statement = extract_financial_data(rows, statement)
    else:
        statement = extract_financial_data_from_text(page_text, statement)

    # Record provenance for newly extracted fields
    after = statement.model_dump()
    for field_name, value in after.items():
        if value is not None and field_name not in before:
            source_line = _find_source_line(page_text, field_name)
            provenance[field_name] = FieldProvenance(
                value=value,
                page_number=page_idx + 1,  # 1-indexed for display
                source_text=source_line,
                extraction_method="regex",
                confidence=0.95 if source_line else 0.7,
            )

    return statement


def _find_source_line(text: str, field_name: str) -> str:
    """Find the line in the text that likely contains this field."""
    from field_synonyms import FIELD_SYNONYMS

    synonyms = FIELD_SYNONYMS.get(field_name, [])
    for line in text.split("\n"):
        line_lower = line.strip().lower()
        for syn in synonyms:
            if line_lower.startswith(syn):
                return line.strip()
    return ""


def _get_missing_fields(statement: FinancialStatement) -> list[str]:
    """Return field names that are still None."""
    return [k for k, v in statement.model_dump().items() if v is None]


def run_extraction_pipeline(pdf_path: str) -> FinancialStatement:
    """Simplified entry point — returns just the FinancialStatement for backward compatibility."""
    result = run_full_pipeline(pdf_path)
    return result.statement


def run_full_pipeline(pdf_path: str) -> ExtractionResult:
    """Run the full extraction pipeline with provenance tracking.

    Returns an ExtractionResult with statement, provenance per field, and any warnings.
    """
    result = ExtractionResult()
    provenance = {}

    # --- Step 1: Text extraction ---
    pages_text = extract_text_pdfplumber(pdf_path)

    if not has_extractable_text(pages_text):
        # OCR fallback for scanned PDFs
        try:
            from ocr_extractor import ocr_pdf_pages
            logger.info("No extractable text found — attempting OCR")
            pages_text = ocr_pdf_pages(pdf_path)
            if not has_extractable_text(pages_text):
                result.warnings.append("PDF appears to be scanned and OCR produced insufficient text.")
                return result
            result.warnings.append("Used OCR to extract text from scanned PDF.")
        except Exception as e:
            logger.warning("OCR fallback failed: %s", e)
            result.warnings.append(f"PDF appears to be scanned. OCR failed: {str(e)}")
            return result

    # --- Step 2: Page classification ---
    bs_page_idx = find_statement_page(pages_text, "balance_sheet")
    is_page_idx = find_statement_page(pages_text, "income_statement")

    logger.info(
        "Page classification: BS=%d, IS=%d (of %d pages)",
        bs_page_idx, is_page_idx, len(pages_text),
    )

    statement = FinancialStatement()

    # --- Step 3: Stage 1 — Regex/synonym extraction ---
    with pdfplumber.open(pdf_path) as pdf:
        if bs_page_idx != -1:
            statement = _extract_from_page(
                pdf.pages[bs_page_idx], pages_text[bs_page_idx],
                bs_page_idx, statement, provenance,
            )

        if is_page_idx != -1:
            statement = _extract_from_page(
                pdf.pages[is_page_idx], pages_text[is_page_idx],
                is_page_idx, statement, provenance,
            )

    regex_populated = sum(1 for v in statement.model_dump().values() if v is not None)
    logger.info("Stage 1 (regex): %d/%d fields populated", regex_populated, len(FinancialStatement.model_fields))

    # --- Step 4: Stage 2 — LLM fallback for missing fields ---
    missing = _get_missing_fields(statement)
    if missing:
        try:
            from llm_extractor import extract_via_llm

            # Feed the relevant page texts to the LLM
            page_texts = []
            if bs_page_idx != -1:
                page_texts.append(pages_text[bs_page_idx])
            if is_page_idx != -1:
                page_texts.append(pages_text[is_page_idx])

            combined_text = "\n\n---\n\n".join(page_texts)

            llm_statement, llm_provenance = extract_via_llm(
                combined_text,
                "financial_statement",
                missing_fields=missing,
            )

            # Merge LLM results into the statement (only for fields still None)
            for field_name in missing:
                llm_value = getattr(llm_statement, field_name, None)
                if llm_value is not None:
                    setattr(statement, field_name, llm_value)
                    # Record LLM provenance
                    prov_data = llm_provenance.get(field_name, {})
                    provenance[field_name] = FieldProvenance(
                        value=llm_value,
                        page_number=bs_page_idx + 1 if bs_page_idx != -1 else None,
                        source_text=prov_data.get("source_text", ""),
                        extraction_method="llm",
                        confidence=prov_data.get("confidence", 0.85),
                    )

            llm_populated = sum(1 for v in statement.model_dump().values() if v is not None) - regex_populated
            logger.info("Stage 2 (LLM): %d additional fields populated", llm_populated)

        except Exception as e:
            logger.warning("LLM extraction failed: %s", e)
            result.warnings.append(f"LLM extraction unavailable: {str(e)}")

    # --- Step 5: Validation ---
    validation = validate_statement(statement)
    if not validation.passed:
        for failure in validation.failures:
            result.warnings.append(failure["message"])

        # Mark affected fields as low confidence
        for field_name in validation.low_confidence_fields:
            if field_name in provenance:
                provenance[field_name].confidence = min(
                    provenance[field_name].confidence or 0.5, 0.5
                )

        # Try LLM re-extraction for low-confidence fields
        if validation.low_confidence_fields:
            try:
                from llm_extractor import extract_via_llm

                page_texts = []
                if bs_page_idx != -1:
                    page_texts.append(pages_text[bs_page_idx])
                if is_page_idx != -1:
                    page_texts.append(pages_text[is_page_idx])

                combined_text = "\n\n---\n\n".join(page_texts)
                validation_context = "\n".join(
                    f"VALIDATION FAILURE: {f['message']}" for f in validation.failures
                )
                combined_text += f"\n\n{validation_context}"

                retry_fields = list(validation.low_confidence_fields)
                llm_stmt, llm_prov = extract_via_llm(
                    combined_text, "financial_statement", missing_fields=retry_fields
                )

                for field_name in retry_fields:
                    llm_val = getattr(llm_stmt, field_name, None)
                    if llm_val is not None and llm_val != getattr(statement, field_name, None):
                        setattr(statement, field_name, llm_val)
                        provenance[field_name] = FieldProvenance(
                            value=llm_val,
                            page_number=provenance.get(field_name, FieldProvenance()).page_number,
                            source_text=llm_prov.get(field_name, {}).get("source_text", ""),
                            extraction_method="llm_retry",
                            confidence=0.6,
                        )

                # Re-validate after retry
                revalidation = validate_statement(statement)
                if not revalidation.passed:
                    for failure in revalidation.failures:
                        if failure["message"] not in result.warnings:
                            result.warnings.append(f"[Still failing after retry] {failure['message']}")

            except Exception as e:
                logger.warning("LLM retry extraction failed: %s", e)

    result.statement = statement
    result.provenance = provenance

    total_populated = sum(1 for v in statement.model_dump().values() if v is not None)
    logger.info("Pipeline complete: %d/%d fields populated", total_populated, len(FinancialStatement.model_fields))

    return result