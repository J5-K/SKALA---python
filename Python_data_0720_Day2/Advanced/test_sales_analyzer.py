import pandas as pd

from sales_analyzer import analyze_sales, clean_sales, percent_change


def sample_data() -> pd.DataFrame:
    return pd.DataFrame({
        "order_id": ["A", "B", "C"],
        "order_date": ["2025-01-01", "2025-01-02", "2025-01-03"],
        "region": ["Seoul", None, "Busan"],
        "category": ["Food", "Food", "Home"],
        "quantity": [1, 2, 1],
        "unit_price": [1000, -1, 3000],
        "discount": [0, 0.1, None],
    })


def test_clean_sales_fills_invalid_price_and_region():
    cleaned = clean_sales(sample_data())
    assert cleaned.loc[1, "unit_price"] == 1000
    assert cleaned.loc[1, "region"] == "Unknown"
    assert cleaned.loc[1, "sales_amount"] == 1800


def test_percent_change_handles_zero():
    assert percent_change(120, 100) == 20
    assert percent_change(120, 0) is None


def test_analysis_returns_briefing_and_status():
    result = analyze_sales(clean_sales(sample_data()), comparison_days=2, z_limit=2)
    assert result["insights"]
    assert result["status"] in {"normal", "warning", "danger"}
    assert len(result["daily_rows"]) == 3
