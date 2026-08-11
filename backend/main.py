"""
FinScope API — FastAPI application.
"""
import tempfile
import os
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, File, UploadFile, HTTPException, Depends, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from config import get_settings
from database import engine, get_db, Base
from db_models import User, Report, ExtractedField
from auth import router as auth_router, get_current_user, get_optional_user
from pipeline import run_extraction_pipeline, run_full_pipeline
from ratio_engine import calculate_ratios

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("finscope")

# ---------------------------------------------------------------------------
# App setup
# ---------------------------------------------------------------------------
settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Create database tables on startup (for local dev with SQLite)."""
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables created / verified.")
    yield


app = FastAPI(
    title="FinScope API",
    description="AI-powered financial statement analysis",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS — allow_credentials=True requires an explicit origin, not "*"
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_origin],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Auth routes
app.include_router(auth_router)


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------
@app.get("/health")
def health():
    return {"status": "ok"}


# ---------------------------------------------------------------------------
# Analyze — upload a PDF and extract financial data
# ---------------------------------------------------------------------------
MAX_UPLOAD_SIZE = 20 * 1024 * 1024  # 20 MB


@app.post("/api/analyze")
async def analyze(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: User = Depends(get_optional_user),
):
    """Upload a PDF, extract financial statements, compute ratios, and save."""
    if file.content_type != "application/pdf":
        raise HTTPException(status_code=400, detail="Only PDF files allowed")

    contents = await file.read()

    if len(contents) > MAX_UPLOAD_SIZE:
        raise HTTPException(status_code=400, detail="File too large (max 20 MB)")

    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        tmp.write(contents)
        tmp_path = tmp.name

    try:
        extraction = run_full_pipeline(tmp_path)
        ratios = calculate_ratios(extraction.statement)
    except Exception as e:
        logger.exception("Pipeline failed for %s", file.filename)
        raise HTTPException(status_code=500, detail=f"Extraction failed: {str(e)}")
    finally:
        os.remove(tmp_path)

    # Persist if user is authenticated
    report_id = None
    if user is not None:
        report = Report(
            user_id=user.id,
            source_type="upload",
            filename=file.filename,
        )
        db.add(report)
        db.commit()
        db.refresh(report)
        report_id = report.id

        # Save each extracted field with provenance
        for field_name, value in extraction.statement.model_dump().items():
            if value is not None:
                prov = extraction.provenance.get(field_name)
                ef = ExtractedField(
                    report_id=report.id,
                    field_name=field_name,
                    value=value,
                    page_number=prov.page_number if prov else None,
                    source_text=prov.source_text if prov else None,
                    extraction_method=prov.extraction_method if prov else "regex",
                    confidence=prov.confidence if prov else None,
                )
                db.add(ef)
        db.commit()

    # Build provenance response
    provenance_response = {}
    for field_name, prov in extraction.provenance.items():
        provenance_response[field_name] = prov.model_dump()

    return {
        "report_id": report_id,
        "statement": extraction.statement.model_dump(),
        "ratios": ratios,
        "provenance": provenance_response,
        "warnings": extraction.warnings,
    }


# ---------------------------------------------------------------------------
# Reports — list & retrieve user's past reports
# ---------------------------------------------------------------------------
@app.get("/api/reports")
def list_reports(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """List all reports for the authenticated user."""
    reports = (
        db.query(Report)
        .filter(Report.user_id == user.id)
        .order_by(Report.created_at.desc())
        .all()
    )
    return [
        {
            "id": r.id,
            "source_type": r.source_type,
            "ticker": r.ticker,
            "filename": r.filename,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        }
        for r in reports
    ]


@app.get("/api/reports/{report_id}")
def get_report(
    report_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Get a specific report with its extracted fields and ratios."""
    report = (
        db.query(Report)
        .filter(Report.id == report_id, Report.user_id == user.id)
        .first()
    )
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")

    fields = db.query(ExtractedField).filter(ExtractedField.report_id == report_id).all()

    # Reconstruct the statement from extracted fields
    from models import FinancialStatement
    statement = FinancialStatement()
    for f in fields:
        if hasattr(statement, f.field_name):
            setattr(statement, f.field_name, f.value)

    ratios = calculate_ratios(statement)

    return {
        "report_id": report.id,
        "source_type": report.source_type,
        "ticker": report.ticker,
        "filename": report.filename,
        "created_at": report.created_at.isoformat() if report.created_at else None,
        "statement": statement.model_dump(),
        "ratios": ratios,
        "fields": [
            {
                "field_name": f.field_name,
                "value": f.value,
                "page_number": f.page_number,
                "source_text": f.source_text,
                "extraction_method": f.extraction_method,
                "confidence": f.confidence,
            }
            for f in fields
        ],
    }


# ---------------------------------------------------------------------------
# EDGAR — search by ticker
# ---------------------------------------------------------------------------
@app.get("/api/filings/{ticker}")
def fetch_filing(
    ticker: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Look up a ticker on SEC EDGAR, download the latest 10-K, and extract data."""
    from edgar_client import fetch_10k_for_ticker

    result = fetch_10k_for_ticker(ticker.upper())
    if not result:
        raise HTTPException(status_code=404, detail=f"No 10-K found for ticker: {ticker}")

    content = result["content"]
    filing_info = result["filing_info"]

    # The filing might be HTML — save it and try to process
    suffix = ".htm" if not content[:5] == b"%PDF-" else ".pdf"

    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(content)
        tmp_path = tmp.name

    try:
        if suffix == ".pdf":
            extraction = run_full_pipeline(tmp_path)
        else:
            # HTML filing — extract text directly
            from models import ExtractionResult
            from statement_extractor import extract_financial_data_from_text
            from models import FinancialStatement
            text = content.decode("utf-8", errors="ignore")
            # Strip HTML tags for text extraction
            import re
            clean_text = re.sub(r"<[^>]+>", " ", text)
            clean_text = re.sub(r"\s+", " ", clean_text)
            extraction = ExtractionResult()
            extraction.statement = extract_financial_data_from_text(clean_text)

        ratios = calculate_ratios(extraction.statement)
    except Exception as e:
        logger.exception("EDGAR pipeline failed for %s", ticker)
        raise HTTPException(status_code=500, detail=f"Extraction failed: {str(e)}")
    finally:
        os.remove(tmp_path)

    # Persist the report
    report = Report(
        user_id=user.id,
        source_type="edgar",
        ticker=ticker.upper(),
        filename=filing_info.get("company_name", ticker),
    )
    db.add(report)
    db.commit()
    db.refresh(report)

    for field_name, value in extraction.statement.model_dump().items():
        if value is not None:
            prov = extraction.provenance.get(field_name)
            ef = ExtractedField(
                report_id=report.id,
                field_name=field_name,
                value=value,
                page_number=prov.page_number if prov else None,
                source_text=prov.source_text if prov else None,
                extraction_method=prov.extraction_method if prov else "regex",
                confidence=prov.confidence if prov else None,
            )
            db.add(ef)
    db.commit()

    provenance_response = {}
    for field_name, prov in extraction.provenance.items():
        provenance_response[field_name] = prov.model_dump()

    return {
        "report_id": report.id,
        "ticker": ticker.upper(),
        "company_name": filing_info.get("company_name", ""),
        "filing_date": filing_info.get("filing_date", ""),
        "statement": extraction.statement.model_dump(),
        "ratios": ratios,
        "provenance": provenance_response,
        "warnings": extraction.warnings,
    }


# ---------------------------------------------------------------------------
# Chat — RAG chatbot over report narrative sections
# ---------------------------------------------------------------------------
from pydantic import BaseModel as PydanticBaseModel


class ChatRequest(PydanticBaseModel):
    report_id: str
    question: str


@app.post("/api/chat")
async def chat(
    payload: ChatRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Answer questions about a report using RAG over its narrative sections."""
    report = (
        db.query(Report)
        .filter(Report.id == payload.report_id, Report.user_id == user.id)
        .first()
    )
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")

    try:
        from rag.chat import answer_question
        result = answer_question(payload.report_id, payload.question)
        return result
    except ImportError:
        raise HTTPException(status_code=501, detail="RAG chatbot not yet configured")
    except Exception as e:
        logger.exception("Chat failed for report %s", payload.report_id)
        raise HTTPException(status_code=500, detail=f"Chat failed: {str(e)}")