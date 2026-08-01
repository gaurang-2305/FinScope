def safe_divide(a, b):
    if a is None or b in (None, 0):
        return None
    return round(a / b, 4)

def calculate_ratios(statement) -> dict:
    return {
        "current_ratio": safe_divide(statement.current_assets, statement.current_liabilities),
        "debt_to_equity": safe_divide(statement.total_liabilities, statement.total_equity),
        "net_margin": safe_divide(statement.net_income, statement.revenue),
        "roa": safe_divide(statement.net_income, statement.total_assets),
        "roe": safe_divide(statement.net_income, statement.total_equity),
    }