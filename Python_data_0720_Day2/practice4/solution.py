from pathlib import Path

import pandas as pd


DATA_FILE = Path(__file__).parent / "sales_raw.csv"


print("데이터 파일:", DATA_FILE)
print("파일 존재 여부:", DATA_FILE.exists())

df = pd.read_csv(DATA_FILE)

print("\n===== 1. 행과 열 개수 =====")
print(df.shape)

print("\n===== 2. 컬럼별 자료형과 결측 개수 =====")
df.info()

print("\n===== 3. 수치형 데이터 요약 =====")
print(df.describe())

print("\n===== 4. 컬럼별 결측 개수 =====")
print(df.isna().sum())

print("\n===== 5. 처음 5행 =====")
print(df.head())

print("\n===== 6. 자료형 변환 전 =====")
print(df.dtypes)

# 날짜 자료형으로 변환합니다.
df["order_date"] = pd.to_datetime(
    df["order_date"],
    errors="coerce",
)

# 숫자 자료형으로 변환합니다.
df["quantity"] = pd.to_numeric(
    df["quantity"],
    errors="coerce",
)

df["unit_price"] = pd.to_numeric(
    df["unit_price"],
    errors="coerce",
)

df["discount"] = pd.to_numeric(
    df["discount"],
    errors="coerce",
)

print("\n===== 7. 자료형 변환 후 =====")
print(df.dtypes)

print("\n===== 8. 자료형 변환 후 결측치 =====")
print(df.isna().sum())