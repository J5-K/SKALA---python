import csv
from pathlib import Path
from typing import Iterator
from collections import Counter

DATA_FILE = Path(__file__).parent / "web_logs.csv"


def read_logs(file_path: Path) -> Iterator[dict[str, str]]:
    """CSV 파일을 한 행씩 읽어서 반환합니다."""
    with file_path.open("r", encoding="utf-8-sig", newline="") as file:
        reader = csv.DictReader(file)

        for row in reader:
            yield row


def main() -> None:
    print("데이터 파일:", DATA_FILE)
    print("파일 존재 여부:", DATA_FILE.exists())

    if not DATA_FILE.exists():
        print("오류: web_logs.csv 파일을 찾지 못했습니다.")
        return

    total_count = 0
    error_5xx_count = 0

    status_counts = Counter()
    path_counts = Counter()
    hour_counts = Counter()
    ip_counts = Counter()

    for log in read_logs(DATA_FILE):
        total_count += 1

        status = log["status"]
        path = log["path"]
        ip = log["ip"]
        timestamp = log["timestamp"]

        # 상태코드별 개수
        status_counts[status] += 1

        # 경로별 접속 개수
        path_counts[path] += 1

        # IP별 접속 개수
        ip_counts[ip] += 1

        # timestamp 예: 2026-07-20 13:25:30
        # 11번째부터 13번째 문자까지 가져오면 시간인 "13"이 됩니다.
        hour = timestamp[11:13]
        hour_counts[hour] += 1

        # 상태코드가 5로 시작하면 5xx 오류입니다.
        if status.startswith("5"):
            error_5xx_count += 1

    if total_count > 0:
        error_5xx_rate = error_5xx_count / total_count * 100
    else:
        error_5xx_rate = 0

    print("\n===== 기본 집계 결과 =====")
    print("전체 로그 수:", total_count)
    print("5xx 오류 수:", error_5xx_count)
    print(f"5xx 오류 비율: {error_5xx_rate:.2f}%")

    print("\n===== 상태코드별 개수 =====")
    for status, count in sorted(status_counts.items()):
        print(status, count)

    print("\n===== 경로별 접속 개수 =====")
    for path, count in path_counts.most_common():
        print(path, count)

    print("\n===== 시간대별 접속 개수 =====")
    for hour, count in sorted(hour_counts.items()):
        print(f"{hour}시: {count}건")

    print("\n===== 접속 횟수 상위 IP 10개 =====")
    for rank, (ip, count) in enumerate(ip_counts.most_common(10), start=1):
        print(f"{rank}위: {ip} - {count}건")


if __name__ == "__main__":
    main()