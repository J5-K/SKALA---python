"""Sales Pulse HTML 리포트를 생성하는 실행 파일."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

import pandas as pd
from jinja2 import Environment, FileSystemLoader, select_autoescape

from config import CONFIG, Config
from sales_analyzer import analyze_sales, clean_sales


def make_chart(daily_rows: list[dict], anomaly_rows: list[dict]) -> str:
    """외부 차트 라이브러리 없이 반응형 SVG 매출 차트를 만든다."""
    daily = pd.DataFrame(daily_rows)
    anomaly_dates = {pd.Timestamp(row["order_date"]) for row in anomaly_rows}
    width, height, left, top, bottom = 1000, 360, 70, 20, 45
    plot_width, plot_height = width - left - 20, height - top - bottom
    low, high = float(daily["sales"].min()), float(daily["sales"].max())
    span = high - low or 1

    def point(index: int, sales: float) -> tuple[float, float]:
        x = left + (plot_width * index / max(len(daily) - 1, 1))
        y = top + plot_height - ((sales - low) / span * plot_height)
        return x, y

    points = [point(i, row.sales) for i, row in enumerate(daily.itertuples())]
    polyline = " ".join(f"{x:.1f},{y:.1f}" for x, y in points)
    markers = []
    for index, row in enumerate(daily.itertuples()):
        if pd.Timestamp(row.order_date) in anomaly_dates:
            x, y = points[index]
            markers.append(
                f'<circle cx="{x:.1f}" cy="{y:.1f}" r="7" fill="#ef4444">'
                f'<title>{row.order_date:%Y-%m-%d}: {row.sales:,.0f}원 (이상 매출일)</title></circle>'
            )
    first_date = daily.iloc[0]["order_date"].strftime("%Y-%m-%d")
    last_date = daily.iloc[-1]["order_date"].strftime("%Y-%m-%d")
    return f'''<svg viewBox="0 0 {width} {height}" role="img" aria-label="일별 매출 추이" style="width:100%;height:auto">
      <line x1="{left}" y1="{top}" x2="{left}" y2="{top + plot_height}" stroke="#d0d5dd"/>
      <line x1="{left}" y1="{top + plot_height}" x2="{width - 20}" y2="{top + plot_height}" stroke="#d0d5dd"/>
      <text x="10" y="{top + 8}" fill="#697386" font-size="13">{high:,.0f}원</text>
      <text x="10" y="{top + plot_height}" fill="#697386" font-size="13">{low:,.0f}원</text>
      <polyline points="{polyline}" fill="none" stroke="#4f46e5" stroke-width="3" stroke-linejoin="round"/>
      {''.join(markers)}
      <text x="{left}" y="{height - 12}" fill="#697386" font-size="13">{first_date}</text>
      <text x="{width - 110}" y="{height - 12}" fill="#697386" font-size="13">{last_date}</text>
      <circle cx="{width - 160}" cy="18" r="6" fill="#ef4444"/><text x="{width - 148}" y="23" fill="#697386" font-size="13">이상 매출일</text>
    </svg>'''


def render(result: dict, config: Config = CONFIG) -> Path:
    environment = Environment(
        loader=FileSystemLoader(config.template_dir),
        autoescape=select_autoescape(["html"]),
    )
    template = environment.get_template("insight_report.html")
    generated_at = datetime.now()
    html = template.render(
        title=config.title,
        generated_at=generated_at.strftime("%Y-%m-%d %H:%M:%S"),
        chart_html=make_chart(result["daily_rows"], result["anomaly_rows"]),
        **result,
    )
    config.output_dir.mkdir(parents=True, exist_ok=True)
    path = config.output_dir / f"sales_pulse_{generated_at:%Y%m%d_%H%M%S}.html"
    path.write_text(html, encoding="utf-8")
    return path


def run_once(config: Config = CONFIG) -> Path:
    if not config.data_path.exists():
        raise FileNotFoundError(f"데이터 파일이 없습니다: {config.data_path}")
    cleaned = clean_sales(pd.read_csv(config.data_path))
    result = analyze_sales(cleaned, config.comparison_days, config.anomaly_z_score)
    path = render(result, config)
    print(f"Sales Pulse 리포트 생성 완료: {path}")
    return path


if __name__ == "__main__":
    run_once()
