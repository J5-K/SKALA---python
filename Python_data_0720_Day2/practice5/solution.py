from pathlib import Path
from time import perf_counter

import duckdb
import pandas as pd
import polars as pl


DATA_FILE = Path(__file__).parent / "events_large.csv"


def run_pandas() -> pd.DataFrame:
    """Pandas로 CSV를 읽고 event_type별로 집계합니다."""
    df = pd.read_csv(DATA_FILE)

    return (
        df.groupby("event_type", as_index=False)
        .agg(
            event_count=("event_id", "count"),
            total_amount=("amount", "sum"),
            average_amount=("amount", "mean"),
        )
        .sort_values("event_type")
        .reset_index(drop=True)
    )


def run_polars() -> pd.DataFrame:
    """Polars Lazy API로 CSV를 읽고 집계합니다."""
    result = (
        pl.scan_csv(DATA_FILE)
        .group_by("event_type")
        .agg(
            pl.len().alias("event_count"),
            pl.col("amount").sum().alias("total_amount"),
            pl.col("amount").mean().alias("average_amount"),
        )
        .sort("event_type")
        .collect()
    )

    return result.to_pandas()


def run_duckdb() -> pd.DataFrame:
    """DuckDB SQL로 CSV를 직접 읽고 집계합니다."""
    query = f"""
        SELECT
            event_type,
            COUNT(event_id) AS event_count,
            SUM(amount) AS total_amount,
            AVG(amount) AS average_amount
        FROM read_csv_auto('{DATA_FILE}')
        GROUP BY event_type
        ORDER BY event_type
    """

    return duckdb.sql(query).df()


def measure(function):
    """함수를 실행하고 결과와 실행 시간을 반환합니다."""
    start = perf_counter()
    result = function()
    elapsed = perf_counter() - start

    return result, elapsed


def normalize(result: pd.DataFrame) -> pd.DataFrame:
    """엔진별 결과 형식을 같게 맞춥니다."""
    result = result.copy()

    result["event_count"] = result["event_count"].astype("int64")
    result["total_amount"] = result["total_amount"].astype("float64")
    result["average_amount"] = (
        result["average_amount"]
        .astype("float64")
        .round(6)
    )

    return (
        result.sort_values("event_type")
        .reset_index(drop=True)
    )


def main() -> None:
    print("데이터 파일:", DATA_FILE)
    print("파일 존재 여부:", DATA_FILE.exists())

    if not DATA_FILE.exists():
        print("오류: events_large.csv 파일을 찾지 못했습니다.")
        return

    pandas_result, pandas_time = measure(run_pandas)
    polars_result, polars_time = measure(run_polars)
    duckdb_result, duckdb_time = measure(run_duckdb)

    pandas_result = normalize(pandas_result)
    polars_result = normalize(polars_result)
    duckdb_result = normalize(duckdb_result)

    pd.testing.assert_frame_equal(
        pandas_result,
        polars_result,
        check_dtype=False,
    )

    pd.testing.assert_frame_equal(
        pandas_result,
        duckdb_result,
        check_dtype=False,
    )

    print("\n===== 집계 결과 =====")
    print(pandas_result.to_string(index=False))

    print("\n===== 실행 시간 =====")
    print(f"Pandas : {pandas_time:.4f}초")
    print(f"Polars : {polars_time:.4f}초")
    print(f"DuckDB : {duckdb_time:.4f}초")

    times = {
        "Pandas": pandas_time,
        "Polars": polars_time,
        "DuckDB": duckdb_time,
    }

    fastest = min(times, key=times.get)

    print(f"\n가장 빠른 엔진: {fastest}")
    print("결과 검증: 세 엔진의 집계 결과가 같습니다.")


if __name__ == "__main__":
    main()