"""판매 데이터를 정제하고 매출 변화와 이상 징후를 분석한다."""

from __future__ import annotations

import pandas as pd


REQUIRED_COLUMNS = {
    "order_id",
    "order_date",
    "region",
    "category",
    "quantity",
    "unit_price",
    "discount",
}


def clean_sales(data: pd.DataFrame) -> pd.DataFrame:
    """원본을 보존하면서 분석 가능한 행과 매출액을 만든다."""
    missing = REQUIRED_COLUMNS.difference(data.columns)
    if missing:
        raise ValueError(f"필수 열이 없습니다: {', '.join(sorted(missing))}")

    cleaned = data.copy()
    cleaned["order_date"] = pd.to_datetime(cleaned["order_date"], errors="coerce")
    for column in ("quantity", "unit_price", "discount"):
        cleaned[column] = pd.to_numeric(cleaned[column], errors="coerce")

    cleaned.loc[cleaned["quantity"] <= 0, "quantity"] = pd.NA
    cleaned.loc[cleaned["unit_price"] <= 0, "unit_price"] = pd.NA
    cleaned["discount"] = cleaned["discount"].fillna(0).clip(0, 1)
    cleaned["region"] = cleaned["region"].fillna("Unknown")
    cleaned["category"] = cleaned["category"].fillna("Unknown")

    category_median = cleaned.groupby("category")["unit_price"].transform("median")
    cleaned["unit_price"] = cleaned["unit_price"].fillna(category_median)
    cleaned["unit_price"] = cleaned["unit_price"].fillna(cleaned["unit_price"].median())
    cleaned = cleaned.dropna(subset=["order_date", "quantity", "unit_price"])
    cleaned["sales_amount"] = (
        cleaned["quantity"] * cleaned["unit_price"] * (1 - cleaned["discount"])
    )
    return cleaned.sort_values("order_date").reset_index(drop=True)


def percent_change(current: float, previous: float) -> float | None:
    """0으로 나누는 경우를 피하면서 증감률을 계산한다."""
    if previous == 0:
        return None
    return (current - previous) / previous * 100


def analyze_sales(data: pd.DataFrame, comparison_days: int, z_limit: float) -> dict:
    """대시보드와 자동 브리핑에 필요한 분석 결과를 반환한다."""
    if data.empty:
        raise ValueError("분석할 유효한 판매 데이터가 없습니다.")

    daily = data.groupby("order_date", as_index=False)["sales_amount"].sum()
    daily = daily.rename(columns={"sales_amount": "sales"})
    mean = daily["sales"].mean()
    std = daily["sales"].std()
    daily["z_score"] = 0.0 if pd.isna(std) or std == 0 else (daily["sales"] - mean) / std
    anomalies = daily[daily["z_score"].abs() >= z_limit].copy()
    anomalies["direction"] = anomalies["z_score"].map(
        lambda value: "급증" if value > 0 else "급감"
    )

    last_date = data["order_date"].max()
    current_start = last_date - pd.Timedelta(days=comparison_days - 1)
    previous_start = current_start - pd.Timedelta(days=comparison_days)
    current = data[data["order_date"].between(current_start, last_date)]
    previous = data[data["order_date"].between(previous_start, current_start, inclusive="left")]

    current_sales = float(current["sales_amount"].sum())
    previous_sales = float(previous["sales_amount"].sum())
    overall_change = percent_change(current_sales, previous_sales)

    dimension_rows: dict[str, list[dict]] = {}
    for dimension in ("category", "region"):
        current_group = current.groupby(dimension)["sales_amount"].sum()
        previous_group = previous.groupby(dimension)["sales_amount"].sum()
        frame = pd.concat([current_group, previous_group], axis=1, keys=["current", "previous"]).fillna(0)
        frame["change"] = [percent_change(c, p) for c, p in zip(frame["current"], frame["previous"])]
        frame = frame.reset_index().sort_values("current", ascending=False)
        dimension_rows[dimension] = frame.to_dict(orient="records")

    discount = data.assign(
        discount_group=(data["discount"] * 100).round().astype(int).astype(str) + "%"
    ).groupby("discount_group", as_index=False).agg(
        orders=("order_id", "count"),
        average_sales=("sales_amount", "mean"),
        total_sales=("sales_amount", "sum"),
    )
    discount = discount.sort_values("average_sales", ascending=False)

    category_rows = dimension_rows["category"]
    comparable = [row for row in category_rows if row["change"] is not None]
    best = max(comparable, key=lambda row: row["change"], default=None)
    worst = min(comparable, key=lambda row: row["change"], default=None)

    insights = []
    if overall_change is None:
        insights.append("직전 비교 기간의 매출이 없어 전체 증감률을 계산하지 못했습니다.")
    else:
        word = "증가" if overall_change >= 0 else "감소"
        insights.append(f"최근 {comparison_days}일 매출은 직전 기간보다 {abs(overall_change):.1f}% {word}했습니다.")
    if best:
        insights.append(f"가장 성장한 카테고리는 {best['category']}로, 매출이 {best['change']:+.1f}% 변했습니다.")
    if worst and worst is not best:
        insights.append(f"관찰이 필요한 카테고리는 {worst['category']}로, 매출이 {worst['change']:+.1f}% 변했습니다.")
    if anomalies.empty:
        insights.append("평균에서 크게 벗어난 이상 매출일은 발견되지 않았습니다.")
    else:
        insights.append(f"평균에서 크게 벗어난 이상 매출일이 {len(anomalies)}일 발견되었습니다.")

    status = "normal"
    status_label = "정상"
    if (overall_change is not None and overall_change <= -20) or len(anomalies) >= 3:
        status, status_label = "danger", "위험"
    elif (overall_change is not None and overall_change < 0) or not anomalies.empty:
        status, status_label = "warning", "주의"

    return {
        "kpis": {
            "orders": len(data),
            "total_sales": float(data["sales_amount"].sum()),
            "average_order": float(data["sales_amount"].mean()),
            "change": overall_change,
        },
        "period": {
            "current_start": current_start.strftime("%Y-%m-%d"),
            "current_end": last_date.strftime("%Y-%m-%d"),
            "previous_start": previous_start.strftime("%Y-%m-%d"),
            "previous_end": (current_start - pd.Timedelta(days=1)).strftime("%Y-%m-%d"),
        },
        "daily_rows": daily.to_dict(orient="records"),
        "anomaly_rows": anomalies.to_dict(orient="records"),
        "category_rows": category_rows,
        "region_rows": dimension_rows["region"],
        "discount_rows": discount.to_dict(orient="records"),
        "insights": insights[:3],
        "status": status,
        "status_label": status_label,
    }
