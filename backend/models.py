from pydantic import BaseModel
from typing import Optional


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