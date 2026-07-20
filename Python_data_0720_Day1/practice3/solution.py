import asyncio
import time

USE_REAL_HTTP = False

TOTAL_ITEMS = 60
MAX_CONCURRENT = 10
MAX_RETRIES = 3

REQUEST_DELAY = 0.1
TIMEOUT_SECONDS = 0.3
BACKOFF_BASE = 0.2


async def do_request(item_id: int, attempt: int) -> dict:
    """실제 API 요청을 흉내 내는 함수입니다."""

    if USE_REAL_HTTP:
        raise NotImplementedError(
            "현재 실습은 인터넷이 필요 없는 모의 실행 모드입니다."
        )

    if item_id % 20 == 0 and attempt == 1:
        await asyncio.sleep(0.05)
        raise ConnectionError("모의 연결 오류")

    if item_id % 25 == 0 and attempt == 1:
        await asyncio.sleep(TIMEOUT_SECONDS + 0.2)

    # 정상적인 API 응답 대기 시간을 흉내 냅니다.
    await asyncio.sleep(REQUEST_DELAY)

    return {
        "id": item_id,
        "ok": True,
        "attempt": attempt,
        "data": f"item-{item_id}",
    }


async def fetch_with_retry(
    item_id: int,
    semaphore: asyncio.Semaphore,
) -> dict:
    """타임아웃과 재시도가 포함된 수집 함수입니다."""

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            async with semaphore:
                print(
                    f"[요청] ID={item_id:02d}, "
                    f"시도={attempt}"
                )

                async with asyncio.timeout(TIMEOUT_SECONDS):
                    result = await do_request(item_id, attempt)

                print(
                    f"[성공] ID={item_id:02d}, "
                    f"시도={attempt}"
                )

                return result

        except (TimeoutError, ConnectionError) as error:
            print(
                f"[실패] ID={item_id:02d}, "
                f"시도={attempt}, "
                f"이유={type(error).__name__}"
            )

            if attempt == MAX_RETRIES:
                raise RuntimeError(
                    f"{item_id}번 요청이 "
                    f"{MAX_RETRIES}번 모두 실패했습니다."
                ) from error

            # 0.2초 → 0.4초처럼 대기 시간 
            wait_seconds = BACKOFF_BASE * (2 ** (attempt - 1))

            print(
                f"[대기] ID={item_id:02d}, "
                f"{wait_seconds:.1f}초 후 재시도"
            )

            await asyncio.sleep(wait_seconds)

    # 반복문 구조상 도달하지 않지만 타입 검사를 위해
    raise RuntimeError(f"{item_id}번 요청 처리 실패")


async def main() -> None:
    start_time = time.perf_counter()

    # 동시에 사용할 수 있는 입장권 10개를 만듭니다.
    semaphore = asyncio.Semaphore(MAX_CONCURRENT)

    # 비동기 작업 60개를 준비합니다.
    tasks = [
        fetch_with_retry(item_id, semaphore)
        for item_id in range(1, TOTAL_ITEMS + 1)
    ]

    # 일부 작업이 최종 실패하더라도 전체 작업을 계속합니다.
    results = await asyncio.gather(
        *tasks,
        return_exceptions=True,
    )

    elapsed_time = time.perf_counter() - start_time

    # 정상 결과와 예외를 나눕니다.
    successes = [
        result
        for result in results
        if not isinstance(result, Exception)
    ]

    failures = [
        result
        for result in results
        if isinstance(result, Exception)
    ]

    # 재시도 후 성공한 결과만 찾습니다.
    retried_successes = [
        result
        for result in successes
        if result["attempt"] > 1
    ]

    print("\n" + "=" * 50)
    print("[비동기 수집 최종 결과]")
    print(f"전체 요청: {TOTAL_ITEMS}건")
    print(f"처리 결과: {len(results)}건")
    print(f"최종 성공: {len(successes)}건")
    print(f"최종 실패: {len(failures)}건")
    print(f"재시도 후 성공: {len(retried_successes)}건")
    print(f"동시 요청 제한: {MAX_CONCURRENT}건")
    print(f"걸린 시간: {elapsed_time:.2f}초")

    if retried_successes:
        retried_ids = [
            result["id"]
            for result in retried_successes
        ]
        print(f"재시도한 ID: {retried_ids}")

    if failures:
        print("\n[최종 실패 목록]")

        for failure in failures:
            print(f"- {failure}")


if __name__ == "__main__":
    asyncio.run(main())