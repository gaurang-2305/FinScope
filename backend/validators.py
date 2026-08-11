"""
Accounting-identity self-validation for extracted financial data.

Checks structural invariants like:
  - total_assets ≈ total_liabilities + total_equity
  - current_assets ≤ total_assets
  - sign consistency on net_income
"""
import logging
from models import FinancialStatement

logger = logging.getLogger("finscope.validators")

TOLERANCE = 0.02  # 2% tolerance for rounding differences


class ValidationResult:
    def __init__(self):
        self.failures: list[dict] = []  # {check, message, affected_fields}
        self.low_confidence_fields: set[str] = set()

    @property
    def passed(self) -> bool:
        return len(self.failures) == 0

    def add_failure(self, check: str, message: str, affected_fields: list[str]):
        self.failures.append({
            "check": check,
            "message": message,
            "affected_fields": affected_fields,
        })
        self.low_confidence_fields.update(affected_fields)
        logger.warning("Validation failed [%s]: %s", check, message)


def validate_statement(statement: FinancialStatement) -> ValidationResult:
    """Run all accounting-identity checks on the extracted statement."""
    result = ValidationResult()

    _check_accounting_equation(statement, result)
    _check_current_vs_total_assets(statement, result)
    _check_current_vs_total_liabilities(statement, result)
    _check_income_sign_consistency(statement, result)

    return result


def _check_accounting_equation(stmt: FinancialStatement, result: ValidationResult):
    """total_assets ≈ total_liabilities + total_equity"""
    if stmt.total_assets is None or stmt.total_liabilities is None or stmt.total_equity is None:
        return

    expected = stmt.total_liabilities + stmt.total_equity
    if expected == 0:
        return

    diff_pct = abs(stmt.total_assets - expected) / abs(expected)
    if diff_pct > TOLERANCE:
        result.add_failure(
            "accounting_equation",
            f"Total Assets ({stmt.total_assets:,.0f}) ≠ Total Liabilities ({stmt.total_liabilities:,.0f}) "
            f"+ Total Equity ({stmt.total_equity:,.0f}) = {expected:,.0f} "
            f"(difference: {diff_pct:.1%})",
            ["total_assets", "total_liabilities", "total_equity"],
        )


def _check_current_vs_total_assets(stmt: FinancialStatement, result: ValidationResult):
    """current_assets ≤ total_assets"""
    if stmt.current_assets is None or stmt.total_assets is None:
        return

    if stmt.current_assets > stmt.total_assets * (1 + TOLERANCE):
        result.add_failure(
            "current_assets_bounds",
            f"Current Assets ({stmt.current_assets:,.0f}) > Total Assets ({stmt.total_assets:,.0f})",
            ["current_assets", "total_assets"],
        )


def _check_current_vs_total_liabilities(stmt: FinancialStatement, result: ValidationResult):
    """current_liabilities ≤ total_liabilities"""
    if stmt.current_liabilities is None or stmt.total_liabilities is None:
        return

    if stmt.current_liabilities > stmt.total_liabilities * (1 + TOLERANCE):
        result.add_failure(
            "current_liabilities_bounds",
            f"Current Liabilities ({stmt.current_liabilities:,.0f}) > Total Liabilities ({stmt.total_liabilities:,.0f})",
            ["current_liabilities", "total_liabilities"],
        )


def _check_income_sign_consistency(stmt: FinancialStatement, result: ValidationResult):
    """If revenue is positive and cogs is positive, operating_income should be less than revenue."""
    if stmt.revenue is not None and stmt.operating_income is not None:
        if stmt.revenue > 0 and stmt.operating_income > stmt.revenue:
            result.add_failure(
                "income_sign_consistency",
                f"Operating Income ({stmt.operating_income:,.0f}) > Revenue ({stmt.revenue:,.0f})",
                ["operating_income", "revenue"],
            )

    if stmt.revenue is not None and stmt.net_income is not None:
        if stmt.revenue > 0 and stmt.net_income > stmt.revenue:
            result.add_failure(
                "net_income_bounds",
                f"Net Income ({stmt.net_income:,.0f}) > Revenue ({stmt.revenue:,.0f})",
                ["net_income", "revenue"],
            )
