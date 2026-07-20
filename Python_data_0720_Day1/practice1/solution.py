import csv
from pathlib import Path
from typing import Iterator
from collections import Counter
from functools import reduce

DATA_FILE = Path(__file__).parent / "web_logs.csv"


def read_logs(file_path: Path) -> Iterator[dict[str, str]]:
    """CSV 파일을 한 행씩 읽어서 반환합니다."""
    with file_path.open("r", encoding="utf-8-sig", newline="") as file:
        reader = csv.DictReader(file)

        for row in reader:
            yield row

#default
def accumulate_log(result, log):
    """로그 한 건을 받아 집계 결과에 누적합니다."""
    result["total_count"] += 1

    status = log["status"]
    path = log["path"]
    ip = log["ip"]
    timestamp = log["timestamp"]

    result["status_counts"][status] += 1
    result["path_counts"][path] += 1
    result["ip_counts"][ip] += 1

    hour = timestamp[11:13]
    result["hour_counts"][hour] += 1

    if status.startswith("5"):
        result["error_5xx_count"] += 1

    return result

#최초 집계 상태를 만드는 함수
def create_initial_result():
    """집계를 시작할 때 사용할 빈 결과를 만듭니다."""
    return {
        "total_count": 0,
        "error_5xx_count": 0,
        "status_counts": Counter(),
        "path_counts": Counter(),
        "hour_counts": Counter(),
        "ip_counts": Counter(),
    }

def main() -> None:
    print("데이터 파일:", DATA_FILE)
    print("파일 존재 여부:", DATA_FILE.exists())

    if not DATA_FILE.exists():
        print("오류: web_logs.csv 파일을 찾지 못했습니다.")
        return

    result = reduce(
        accumulate_log,
        read_logs(DATA_FILE),
        create_initial_result(),
    )

    total_count = result["total_count"]
    error_5xx_count = result["error_5xx_count"]

    if total_count > 0:
        error_5xx_rate = error_5xx_count / total_count * 100
    else:
        error_5xx_rate = 0

    print("\n===== 대용량 로그 스트리밍 집계 리포트 =====")
    print("전체 로그 수:", total_count)
    print("5xx 오류 수:", error_5xx_count)
    print(f"5xx 오류 비율: {error_5xx_rate:.2f}%")

    print("\n===== 상태코드별 개수 =====")
    for status, count in sorted(result["status_counts"].items()):
        print(f"{status}: {count}건")

    print("\n===== 경로별 접속 개수 =====")
    for path, count in result["path_counts"].most_common():
        print(f"{path}: {count}건")

    print("\n===== 시간대별 접속 개수 =====")
    for hour, count in sorted(result["hour_counts"].items()):
        print(f"{hour}시: {count}건")

    print("\n===== 접속 횟수 상위 IP 10개 =====")
    for rank, (ip, count) in enumerate(
        result["ip_counts"].most_common(10),
        start=1,
    ):
        print(f"{rank}위: {ip} - {count}건")


if __name__ == "__main__":
    main()