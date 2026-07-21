"""종합실습 2: EDA + 통계 검정 + 이탈 예측 ML 파이프라인."""

from __future__ import annotations

import json
from pathlib import Path

import joblib
import pandas as pd
import plotly.express as px
import plotly.io as pio
import polars as pl
from scipy.stats import chi2_contingency, ttest_ind
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler


BASE_DIR = Path(__file__).parent
DATA_FILE = BASE_DIR / "telco_churn.csv"
OUTPUT_DIR = BASE_DIR / "output"


def run_eda(data: pl.DataFrame) -> tuple[pl.DataFrame, pl.DataFrame]:
    """Polars로 계약 유형과 성별별 이탈률을 요약합니다."""
    contract_summary = (
        data.group_by("contract")
        .agg(
            pl.len().alias("customers"),
            pl.col("churn").mean().alias("churn_rate"),
            pl.col("monthly_charges").mean().alias("avg_monthly_charges"),
        )
        .sort("churn_rate", descending=True)
    )
    gender_summary = (
        data.group_by("gender")
        .agg(
            pl.len().alias("customers"),
            pl.col("churn").mean().alias("churn_rate"),
        )
        .sort("gender")
    )
    return contract_summary, gender_summary


def run_statistics(data: pd.DataFrame) -> dict[str, float]:
    """월 요금 t검정과 계약 유형 카이제곱 검정을 수행합니다."""
    stayed = data.loc[data["churn"] == 0, "monthly_charges"].dropna()
    churned = data.loc[data["churn"] == 1, "monthly_charges"].dropna()
    t_stat, t_pvalue = ttest_ind(churned, stayed, equal_var=False)

    table = pd.crosstab(data["contract"], data["churn"])
    chi2, chi2_pvalue, _, _ = chi2_contingency(table)

    return {
        "t_statistic": float(t_stat),
        "t_pvalue": float(t_pvalue),
        "chi2_statistic": float(chi2),
        "chi2_pvalue": float(chi2_pvalue),
    }


def train_model(data: pd.DataFrame) -> tuple[Pipeline, float]:
    """전처리와 RandomForest를 한 파이프라인으로 묶어 학습합니다."""
    x = data.drop(columns=["customer_id", "churn"])
    y = data["churn"]

    numeric_columns = x.select_dtypes(include="number").columns.tolist()
    categorical_columns = x.select_dtypes(exclude="number").columns.tolist()

    numeric_pipeline = Pipeline(
        [
            ("imputer", SimpleImputer(strategy="median")),
            ("scaler", StandardScaler()),
        ]
    )
    categorical_pipeline = Pipeline(
        [
            ("imputer", SimpleImputer(strategy="most_frequent")),
            (
                "onehot",
                OneHotEncoder(handle_unknown="ignore"),
            ),
        ]
    )
    preprocessor = ColumnTransformer(
        [
            ("numeric", numeric_pipeline, numeric_columns),
            ("categorical", categorical_pipeline, categorical_columns),
        ]
    )
    pipeline = Pipeline(
        [
            ("preprocessor", preprocessor),
            (
                "model",
                RandomForestClassifier(
                    n_estimators=300,
                    max_depth=8,
                    min_samples_leaf=5,
                    random_state=42,
                    n_jobs=-1,
                ),
            ),
        ]
    )

    x_train, x_test, y_train, y_test = train_test_split(
        x,
        y,
        test_size=0.2,
        random_state=42,
        stratify=y,
    )
    pipeline.fit(x_train, y_train)
    probability = pipeline.predict_proba(x_test)[:, 1]
    auc = roc_auc_score(y_test, probability)
    return pipeline, float(auc)


def save_eda_report(
    data: pd.DataFrame,
    contract_summary: pd.DataFrame,
    statistics: dict[str, float],
    auc: float,
) -> Path:
    """두 개의 Plotly 차트와 핵심 지표를 하나의 HTML로 저장합니다."""
    contract_chart = px.bar(
        contract_summary,
        x="contract",
        y="churn_rate",
        title="계약 유형별 고객 이탈률",
        labels={"contract": "계약 유형", "churn_rate": "이탈률"},
    )
    charge_chart = px.box(
        data,
        x="churn",
        y="monthly_charges",
        color="churn",
        title="이탈 여부별 월 요금 분포",
        labels={"churn": "이탈 여부", "monthly_charges": "월 요금"},
    )
    html = f"""<!doctype html>
<html lang="ko"><head><meta charset="utf-8"><title>종합실습 2 EDA</title>
<style>body{{font-family:Arial,sans-serif;max-width:1100px;margin:40px auto;padding:0 20px}}
.kpi{{display:flex;gap:16px;flex-wrap:wrap}} .card{{padding:16px 20px;background:#f3f6fb;border-radius:12px}}</style>
</head><body><h1>통신 고객 이탈 EDA · 통계 · ML 결과</h1>
<div class="kpi"><div class="card">고객 수<br><b>{len(data):,}</b></div>
<div class="card">전체 이탈률<br><b>{data["churn"].mean():.2%}</b></div>
<div class="card">ROC-AUC<br><b>{auc:.4f}</b></div></div>
<h2>통계 검정</h2><p>월 요금 t검정 p값: {statistics["t_pvalue"]:.3e}</p>
<p>계약 유형 카이제곱 p값: {statistics["chi2_pvalue"]:.3e}</p>
{pio.to_html(contract_chart, full_html=False, include_plotlyjs="cdn")}
{pio.to_html(charge_chart, full_html=False, include_plotlyjs=False)}
</body></html>"""
    path = OUTPUT_DIR / "eda_report.html"
    path.write_text(html, encoding="utf-8")
    return path


def main() -> None:
    if not DATA_FILE.exists():
        raise FileNotFoundError(f"데이터 파일이 없습니다: {DATA_FILE}")
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    polars_data = pl.read_csv(DATA_FILE)
    print(f"[STEP 0] 데이터: {polars_data.shape[0]:,}행 × {polars_data.shape[1]}열")
    print(polars_data.head())

    contract_pl, gender_pl = run_eda(polars_data)
    print("\n[STEP 1] Polars EDA - 계약 유형별")
    print(contract_pl)
    print("\n[STEP 1] Polars EDA - 성별")
    print(gender_pl)

    pandas_data = polars_data.to_pandas()
    statistics = run_statistics(pandas_data)
    print("\n[STEP 2] 통계 검정")
    print(f"t검정 p값: {statistics['t_pvalue']:.3e}")
    print(f"카이제곱 p값: {statistics['chi2_pvalue']:.3e}")

    model, auc = train_model(pandas_data)
    print("\n[STEP 3] ML 파이프라인")
    print(f"ROC-AUC: {auc:.4f}")

    model_path = OUTPUT_DIR / "churn_model.joblib"
    metrics_path = OUTPUT_DIR / "metrics.json"
    joblib.dump(model, model_path)
    metrics_path.write_text(
        json.dumps({**statistics, "roc_auc": auc}, indent=2),
        encoding="utf-8",
    )
    report_path = save_eda_report(
        pandas_data,
        contract_pl.to_pandas(),
        statistics,
        auc,
    )
    print("\n[STEP 4] 결과 저장")
    print(f"모델: {model_path}")
    print(f"지표: {metrics_path}")
    print(f"HTML: {report_path}")


if __name__ == "__main__":
    main()