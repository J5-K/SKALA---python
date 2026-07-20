"""종합실습 1: 비동기 수집 -> 검증 -> 파일 저장 ETL 파이프라인."""

import asyncio
from pathlib import Path
from typing import Any

import pandas as pd
from pydantic import ValidationError

from models import Product


TOTAL_ITEMS = 60
MAX_CONCURRENT = 10
MAX_RETRIES = 3
REQUEST_DELAY = 0.05


async def fetch(item_id: int, attempt: int) -> dict[str, Any]:
    """인터넷 없이 API 응답 한 건을 흉내 냅니다."""

    await asyncio.sleep(REQUEST_DELAY)  # 서버 응답을 기다리는 상황입니다.

    # 20, 40, 60번은 첫 요청만 실패시켜 재시도 동작을 확인합니다.
    if item_id % 20 == 0 and attempt == 1:
        raise ConnectionError("일시적인 모의 네트워크 오류")

    categories = [" FOOD ", "Book", "digital", "LIVING"]

    return {
        "id": item_id,
        "name": f"상품 {item_id}",
        "category": categories[(item_id - 1) % len(categories)],
        # 17의 배수는 일부러 음수 가격을 넣어 Pydantic이 걸러내게 합니다.
        "price": -500.0 if item_id % 17 == 0 else 1_000.0 + item_id * 100,
    }


async def extract(
    ids: list[int],
    max_concurrent: int = MAX_CONCURRENT,
) -> list[dict[str, Any]]:
    """E: 여러 상품을 동시에 수집하되 동시 요청 수를 제한합니다."""

    semaphore = asyncio.Semaphore(max_concurrent)  # 입장권을 10장만 만듭니다.

    async def fetch_one(item_id: int) -> dict[str, Any]:
        for attempt in range(1, MAX_RETRIES + 1):
            try:
                async with semaphore:
                    # 한 요청을 0.3초 이상 기다리지 않습니다.
                    async with asyncio.timeout(0.3):
                        return await fetch(item_id, attempt)
            except (ConnectionError, TimeoutError):
                if attempt == MAX_RETRIES:
                    raise

                # 실패할수록 0.1초, 0.2초처럼 조금 더 기다렸다 재시도합니다.
                await asyncio.sleep(0.1 * (2 ** (attempt - 1)))

        raise RuntimeError(f"{item_id}번 수집 실패")

    tasks = [fetch_one(item_id) for item_id in ids]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    # 한 요청이 최종 실패해도 성공한 결과는 그대로 살립니다.
    return [result for result in results if not isinstance(result, Exception)]


def transform(
    raw: list[dict[str, Any]],
) -> tuple[list[Product], list[dict[str, Any]]]:
    """T: Pydantic으로 검사하여 정상 데이터와 오염 데이터를 나눕니다."""

    valid: list[Product] = []
    invalid: list[dict[str, Any]] = []

    for row in raw:
        try:
            valid.append(Product.model_validate(row))
        except ValidationError as error:
            invalid.append(
                {
                    "data": row,
                    "errors": error.errors(include_url=False),
                }
            )

    return valid, invalid


def load(valid: list[Product], out_dir: str | Path = "output") -> pd.DataFrame:
    """L: 정상 데이터만 DataFrame으로 바꾸고 CSV와 Parquet으로 저장합니다."""

    output_path = Path(out_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    # Pydantic v2에서는 .dict() 대신 .model_dump()를 사용합니다.
    dataframe = pd.DataFrame([product.model_dump() for product in valid])
    dataframe.to_csv(output_path / "products.csv", index=False, encoding="utf-8-sig")
    dataframe.to_parquet(output_path / "products.parquet", index=False)
    return dataframe


async def run(
    ids: list[int],
    out_dir: str | Path | None = None,
) -> dict[str, int]:
    """E, T, L을 순서대로 부르는 조율 함수입니다."""

    if out_dir is None:
        out_dir = Path(__file__).parent / "output"

    raw = await extract(ids)                 # E: 비동기 수집
    valid, invalid = transform(raw)          # T: 정상/오염 분리
    dataframe = load(valid, out_dir)         # L: CSV와 Parquet 저장

    return {
        "total": len(raw),
        "valid": len(valid),
        "invalid": len(invalid),
        "rows_saved": len(dataframe),
    }


def main() -> None:
    ids = list(range(1, TOTAL_ITEMS + 1))
    summary = asyncio.run(run(ids))

    print("[종합실습 1 - 비동기 ETL 결과]")
    print(f"수집: {summary['total']}건")
    print(f"유효: {summary['valid']}건")
    print(f"오염: {summary['invalid']}건")
    print(f"저장: {summary['rows_saved']}건")


if __name__ == "__main__":
    main()

