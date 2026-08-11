"""
Phase 0 smoke tests — verify the extraction pipeline works end-to-end.
"""
import os
import pytest
from pipeline import run_extraction_pipeline


SAMPLE_PDF = os.path.join(os.path.dirname(__file__), "test_data", "sample_report.pdf")


# ---------------------------------------------------------------------------
# Unit test: pipeline directly
# ---------------------------------------------------------------------------
class TestPipelineDirect:
    @pytest.mark.skipif(not os.path.exists(SAMPLE_PDF), reason="No sample PDF")
    def test_extraction_returns_financial_statement(self):
        """run_extraction_pipeline returns a FinancialStatement with at least some populated fields."""
        statement = run_extraction_pipeline(SAMPLE_PDF)
        populated = {k: v for k, v in statement.model_dump().items() if v is not None}
        assert len(populated) > 0, (
            f"Pipeline returned all-None fields. Statement: {statement.model_dump()}"
        )

    @pytest.mark.skipif(not os.path.exists(SAMPLE_PDF), reason="No sample PDF")
    def test_balance_sheet_fields_present(self):
        """At least one balance-sheet field should be extracted."""
        statement = run_extraction_pipeline(SAMPLE_PDF)
        bs_fields = [
            statement.total_assets,
            statement.current_assets,
            statement.total_liabilities,
            statement.current_liabilities,
            statement.total_equity,
        ]
        assert any(f is not None for f in bs_fields), (
            "No balance-sheet fields were extracted."
        )


# ---------------------------------------------------------------------------
# Integration test: through the /api/analyze endpoint
# ---------------------------------------------------------------------------
class TestAnalyzeEndpoint:
    @pytest.mark.skipif(not os.path.exists(SAMPLE_PDF), reason="No sample PDF")
    def test_analyze_returns_200_with_data(self, client):
        """Uploading a real PDF through /api/analyze returns 200 with statement + ratios."""
        with open(SAMPLE_PDF, "rb") as f:
            response = client.post(
                "/api/analyze",
                files={"file": ("sample_report.pdf", f, "application/pdf")},
            )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"

        data = response.json()
        assert "statement" in data, "Response missing 'statement' key"
        assert "ratios" in data, "Response missing 'ratios' key"

        # At least one field should be non-null
        populated = {k: v for k, v in data["statement"].items() if v is not None}
        assert len(populated) > 0, (
            f"Endpoint returned all-None statement: {data['statement']}"
        )

    def test_analyze_rejects_non_pdf(self, client):
        """Non-PDF uploads should be rejected with 400."""
        response = client.post(
            "/api/analyze",
            files={"file": ("test.txt", b"not a pdf", "text/plain")},
        )
        assert response.status_code == 400
