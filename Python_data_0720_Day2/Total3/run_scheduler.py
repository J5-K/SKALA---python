"""한 번 실행, 간격 반복, 매일 지정 시각 실행을 한 진입점으로 제공합니다."""

import argparse
import time

import schedule

from report import run_once


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--interval", type=int, default=0, help="반복 간격(초)")
    parser.add_argument("--daily", help="매일 실행할 시각(HH:MM)")
    args = parser.parse_args()

    if args.daily:
        schedule.every().day.at(args.daily).do(run_once)
        print(f"매일 {args.daily}에 실행합니다. 종료: Ctrl+C")
        while True:
            schedule.run_pending()
            time.sleep(1)

    if args.interval > 0:
        print(f"{args.interval}초마다 실행합니다. 종료: Ctrl+C")
        while True:
            run_once()
            time.sleep(args.interval)

    run_once()


if __name__ == "__main__":
    main()
