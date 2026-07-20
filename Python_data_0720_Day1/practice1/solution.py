import csv
from pathlib import Path


# 현재 solution.py와 같은 폴더에 있는 CSV 파일을 찾습니다.
DATA_FILE = Path(__file__).parent / "web_logs.csv"


print("데이터 파일 위치:", DATA_FILE)
print("파일 존재 여부:", DATA_FILE.exists())

with DATA_FILE.open("r", encoding="utf-8-sig", newline="") as file:
    reader = csv.DictReader(file)

    print("열 이름:", reader.fieldnames)
    print("\n처음 5개 데이터:")

    for number, row in enumerate(reader, start=1):
        print(number, row)

        if number == 5:
            break