"""종합실습 1의 주요 기능을 확인하는 테스트입니다."""

import asyncio

import pandas as pd

from pipeline import extract, load, run, transform


def test_category_is_normalized() -> None:
    valid, _ = transform(
        [{"id": 1, "name": "상품", "category": " FOOD ", "price": 1000}]
    )
    assert valid[0].category == "food"


def test_negative_price_is_rejected() -> None:
    valid, invalid = transform(
        [{"id": 1, "name": "상품", "category": "food", "price": -100}]
    )
    assert len(valid) == 0
    assert len(invalid) == 1


def test_valid_and_invalid_are_split() -> None:
    rows = [
        {"id": 1, "name": "정상", "category": "book", "price": 1000},
        {"id": 2, "name": "오염", "category": "book", "price": -1},
    ]
    valid, invalid = transform(rows)
    assert (len(valid), len(invalid)) == (1, 1)


def test_extract_collects_all_items() -> None:
    results = asyncio.run(extract(list(range(1, 61))))
    assert len(results) == 60


def test_load_creates_csv_and_parquet(tmp_path) -> None:
    valid, _ = transform([{"id": 1, "name": "상품", "category": "food", "price": 1000}])
    load(valid, tmp_path)
    assert (tmp_path / "products.csv").exists()
    assert (tmp_path / "products.parquet").exists()


def test_parquet_round_trip_and_run(tmp_path) -> None:
    summary = asyncio.run(run(list(range(1, 61)), tmp_path))
    saved = pd.read_parquet(tmp_path / "products.parquet")

    assert summary == {"total": 60, "valid": 57, "invalid": 3, "rows_saved": 57}
    assert len(saved) == 57
    assert saved["price"].dtype.kind == "f"
