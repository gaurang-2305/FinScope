from pydantic import BaseModel
from typing import Optional


class FieldProvenance(BaseModel):
    """Provenance metadata for a single extracted field."""
    value: Optional[float] = None
    page_number: Optional[int] = None
    source_text: Optional[str] = None
    extraction_method: Optional[str] = None  # "regex" | "llm"
    confidence: Optional[float] = None


class FinancialStatement(BaseModel):
    total_assets: Optional[float] = None
    current_assets: Optional[float] = None
    total_liabilities: Optional[float] = None
    current_liabilities: Optional[float] = None
    total_equity: Optional[float] = None

    revenue: Optional[float] = None
    cogs: Optional[float] = None
    operating_income: Optional[float] = None
    net_income: Optional[float] = None


class ExtractionResult(BaseModel):
    """Full extraction result with provenance tracking."""
    statement: FinancialStatement = FinancialStatement()
    provenance: dict[str, FieldProvenance] = {}
    warnings: list[str] = []