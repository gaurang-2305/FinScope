"""
LLM-based structured extraction using Anthropic Claude.

Falls back to LLM extraction for fields that regex/synonym matching couldn't populate.
Returns structured data matching FinancialStatement schema with provenance metadata.
"""
import json
import logging
from typing import Optional

from models import FinancialStatement
from config import get_settings

logger = logging.getLogger("finscope.llm")


def _build_system_prompt(statement_type: str) -> str:
    schema = FinancialStatement.model_json_schema()
    return f"""You are a financial data extraction expert. Your task is to extract 
financial data from the provided text of a {statement_type}.

You must return ONLY valid JSON matching this exact schema:
{json.dumps(schema, indent=2)}

Rules:
- Extract the most recent year's figures only.
- Values should be raw numbers (not formatted strings). For example: 512163, not "$512,163".
- Use negative numbers for losses or deficits (not parenthetical notation).
- If a field cannot be determined from the text, set it to null.
- Do NOT make up or estimate values. Only extract what is explicitly stated.
- Return ONLY the JSON object, no markdown fences, no explanation."""


def _build_user_prompt(text: str, missing_fields: list[str]) -> str:
    fields_str = ", ".join(missing_fields)
    return f"""Extract the following fields from this financial statement text: {fields_str}

TEXT:
{text}

Return the complete JSON with all fields. Set fields you cannot find to null."""


def extract_via_llm(
    table_text: str,
    statement_type: str,
    missing_fields: Optional[list[str]] = None,
) -> tuple[FinancialStatement, dict]:
    """Extract financial data using Claude LLM.
    
    Args:
        table_text: Raw text from the financial statement page
        statement_type: "balance_sheet" or "income_statement"
        missing_fields: Optional list of specific fields to focus on
        
    Returns:
        Tuple of (FinancialStatement, provenance_dict)
        provenance_dict maps field_name -> {"source_text": str, "confidence": float}
    """
    settings = get_settings()
    
    if not settings.anthropic_api_key:
        logger.warning("No ANTHROPIC_API_KEY set — skipping LLM extraction")
        return FinancialStatement(), {}

    try:
        import anthropic
    except ImportError:
        logger.warning("anthropic package not installed — skipping LLM extraction")
        return FinancialStatement(), {}

    client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
    
    system_prompt = _build_system_prompt(statement_type)
    
    if missing_fields:
        user_prompt = _build_user_prompt(table_text, missing_fields)
    else:
        user_prompt = f"Extract all financial data from this text:\n\n{table_text}"

    provenance = {}
    
    # Attempt extraction with one retry on parse failure
    for attempt in range(2):
        try:
            response = client.messages.create(
                model="claude-sonnet-4-6-20250514",
                max_tokens=1024,
                system=system_prompt,
                messages=[{"role": "user", "content": user_prompt}],
                temperature=0,
            )
            
            raw_text = response.content[0].text.strip()
            
            # Strip markdown fences if present
            if raw_text.startswith("```"):
                lines = raw_text.split("\n")
                raw_text = "\n".join(lines[1:-1]) if lines[-1].strip() == "```" else "\n".join(lines[1:])
            
            data = json.loads(raw_text)
            statement = FinancialStatement.model_validate(data)
            
            # Build provenance for fields that were extracted
            for field_name, value in statement.model_dump().items():
                if value is not None:
                    provenance[field_name] = {
                        "source_text": _find_source_line(table_text, field_name, value),
                        "confidence": 0.85,  # LLM confidence baseline
                        "extraction_method": "llm",
                    }
            
            logger.info(
                "LLM extraction succeeded (attempt %d): %d fields populated",
                attempt + 1,
                sum(1 for v in statement.model_dump().values() if v is not None),
            )
            return statement, provenance
            
        except (json.JSONDecodeError, Exception) as e:
            if attempt == 0:
                # Retry with error context appended
                user_prompt += f"\n\nYour previous response failed to parse: {str(e)}\nPlease return ONLY valid JSON."
                logger.warning("LLM extraction attempt 1 failed: %s — retrying", e)
            else:
                logger.error("LLM extraction failed after 2 attempts: %s", e)
    
    return FinancialStatement(), {}


def _find_source_line(text: str, field_name: str, value: float) -> str:
    """Try to find the source line in the text that contains the extracted value."""
    # Map field names to likely keywords
    field_keywords = {
        "total_assets": ["total assets"],
        "current_assets": ["current assets", "total current assets"],
        "total_liabilities": ["total liabilities"],
        "current_liabilities": ["current liabilities", "total current liabilities"],
        "total_equity": ["equity", "stockholders"],
        "revenue": ["revenue", "net sales", "total revenue"],
        "cogs": ["cost of revenue", "cost of goods", "cost of sales"],
        "operating_income": ["operating income", "income from operations"],
        "net_income": ["net income", "net earnings", "net profit"],
    }
    
    keywords = field_keywords.get(field_name, [field_name.replace("_", " ")])
    
    for line in text.split("\n"):
        line_lower = line.strip().lower()
        for kw in keywords:
            if kw in line_lower:
                return line.strip()
    
    return ""
