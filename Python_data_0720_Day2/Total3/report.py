"""종합실습 3: 매출 집계와 Jinja2 HTML 리포트 생성."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

import pandas as pd
from jinja2 import Environment, FileSystemLoader, select_autoescape

from config import CONFIG, Config


def clean_sales(data: pd.DataFrame) -> pd.DataFrame:
    """원본은 보존하고 리포트에 필요한 최소 정제를 수행합니다."""
    cleaned = data.copy()
    cleaned["quantity"] = pd.to_numeric(cleaned["quantity"], errors="coerce")
    cleaned["unit_price"] = pd.to_numeric(cleaned["unit_price"], errors="coerce")
    cleaned["discount"] = pd.to_numeric(cleaned["discount"], errors="coerce").fillna(0)
    cleaned.loc[cleaned["unit_price"] <= 0, "unit_price"] = pd.NA
    median_by_category = cleaned.groupby("category")["unit_price"].transform("median")
    cleaned["unit_price"] = cleaned["unit_price"].fillna(median_by_category)
    cleaned["region"] = cleaned["region"].fillna("Unknown")
    cleaned["sales_amount"] = (
        cleaned["quantity"] * cleaned["unit_price"] * (1 - cleaned["discount"])
    )
    return cleaned


def aggregate(data: pd.DataFrame, top_n: int) -> dict:
    """템플릿에 전달할 KPI와 카테고리별 매출표를 만듭니다."""
    category = (
        data.groupby("category", as_index=False)
        .agg(
            orders=("order_id", "count"),
            quantity=("quantity", "sum"),
            sales=("sales_amount", "sum"),
        )
        .sort_values("sales", ascending=False)
    )
    category["sales"] = category["sales"].round(2)
    top_regions = (
        data.groupby("region", as_index=False)["sales_amount"]
        .sum()
        .sort_values("sales_amount", ascending=False)
        .head(top_n)
    )
    return {
        "kpis": {
            "orders": int(len(data)),
            "total_quantity": int(data["quantity"].sum()),
            "total_sales": float(data["sales_amount"].sum()),
            "average_order": float(data["sales_amount"].mean()),
        },
        "category_rows": category.to_dict(orient="records"),
        "region_rows": top_regions.to_dict(orient="records"),
    }


def render(data: dict, config: Config = CONFIG) -> Path:
    """Jinja2 템플릿을 렌더링하고 타임스탬프 HTML로 저장합니다."""
    environment = Environment(
        loader=FileSystemLoader(config.template_dir),
        autoescape=select_autoescape(["html"]),
    )
    template = environment.get_template("report.html")
    generated_at = datetime.now()
    html = template.render(
        title=config.title,
        generated_at=generated_at.strftime("%Y-%m-%d %H:%M:%S"),
        **data,
    )
    config.output_dir.mkdir(parents=True, exist_ok=True)
    stamp = generated_at.strftime("%Y%m%d_%H%M%S")
    path = config.output_dir / f"report_{stamp}.html"
    path.write_text(html, encoding="utf-8")
    return path


def run_once(config: Config = CONFIG) -> Path:
    """어떤 스케줄 방식에서도 공통으로 호출하는 단일 실행 함수입니다."""
    if not config.data_path.exists():
        raise FileNotFoundError(f"데이터 파일이 없습니다: {config.data_path}")
    raw = pd.read_csv(config.data_path)
    cleaned = clean_sales(raw)
    result = aggregate(cleaned, config.top_n)
    path = render(result, config)
    print(f"리포트 생성 완료: {path}")
    return path


def main() -> None:
    run_once()


if __name__ == "__main__":
    main()
