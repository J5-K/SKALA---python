from pathlib import Path

import pandas as pd


# Pandas 2.x Copy-on-Write 기능을 활성화합니다.
pd.options.mode.copy_on_write = True


DATA_FILE = Path(__file__).parent / "sales_raw.csv"


def winsorize_iqr(
    dataframe: pd.DataFrame,
    column: str,
) -> tuple[float, float, int]:
    """IQR 범위를 벗어난 값을 하한 또는 상한으로 조정합니다."""
    q1 = dataframe[column].quantile(0.25)
    q3 = dataframe[column].quantile(0.75)
    iqr = q3 - q1

    lower_bound = q1 - 1.5 * iqr
    upper_bound = q3 + 1.5 * iqr

    outlier_mask = (
        (dataframe[column] < lower_bound)
        | (dataframe[column] > upper_bound)
    )

    outlier_count = int(outlier_mask.sum())

    dataframe.loc[:, column] = dataframe[column].clip(
        lower=lower_bound,
        upper=upper_bound,
    )

    return lower_bound, upper_bound, outlier_count


print("데이터 파일:", DATA_FILE)
print("파일 존재 여부:", DATA_FILE.exists())

if not DATA_FILE.exists():
    raise FileNotFoundError(
        "sales_raw.csv 파일을 찾지 못했습니다."
    )


# 원본과 정제용 데이터를 분리합니다.
raw_df = pd.read_csv(DATA_FILE)
df = raw_df.copy()


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
# 변환할 수 없는 값은 NaT로 변경됩니다.
df["order_date"] = pd.to_datetime(
    df["order_date"],
    errors="coerce",
)

# 숫자 자료형으로 변환합니다.
# 변환할 수 없는 값은 NaN으로 변경됩니다.
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

print("\n===== 9. 날짜 변환 확인 =====")
print(df[["order_date"]].head())

print("\n가장 이른 주문일:", df["order_date"].min())
print("가장 늦은 주문일:", df["order_date"].max())


# 날짜 분석용 order_date는 datetime 자료형으로 유지합니다.
# 출력·저장용 컬럼에서는 결측 날짜를 Unknown으로 표시합니다.
df["order_date_display"] = (
    df["order_date"]
    .dt.strftime("%Y-%m-%d")
    .fillna("Unknown")
)

print("\n===== 10. 날짜 결측치 Unknown 처리 =====")
print(df[["order_date", "order_date_display"]].head())
print(
    "Unknown 날짜 개수:",
    (df["order_date_display"] == "Unknown").sum(),
)


print("\n===== 11. 가격 데이터 문제 확인 =====")

missing_price_count = df["unit_price"].isna().sum()
non_positive_price_count = (df["unit_price"] <= 0).sum()

print("가격 결측치:", missing_price_count, "건")
print("0 이하 가격:", non_positive_price_count, "건")
print("가격 최솟값:", df["unit_price"].min())


# 0 이하의 가격은 유효하지 않은 가격으로 보고 결측치로 바꿉니다.
df.loc[
    df["unit_price"] <= 0,
    "unit_price",
] = pd.NA

print("\n0 이하 가격을 결측치로 변경한 후:")
print(
    "가격 결측치:",
    df["unit_price"].isna().sum(),
    "건",
)
print(
    "0 이하 가격:",
    (df["unit_price"] <= 0).sum(),
    "건",
)


print("\n===== 12. 카테고리별 가격 중앙값 =====")

category_price_median = (
    df.groupby("category")["unit_price"]
    .median()
)

print(category_price_median)


# 각 행에 해당 카테고리의 가격 중앙값을 연결합니다.
price_median_by_row = (
    df.groupby("category")["unit_price"]
    .transform("median")
)

# 가격 결측치를 같은 카테고리의 중앙값으로 채웁니다.
df["unit_price"] = df["unit_price"].fillna(
    price_median_by_row
)

print("\n가격 결측치 처리 후:")
print(
    "가격 결측치:",
    df["unit_price"].isna().sum(),
    "건",
)
print("가격 최솟값:", df["unit_price"].min())


# 빈 문자열도 결측치로 통일합니다.
df["region"] = df["region"].replace(
    r"^\s*$",
    pd.NA,
    regex=True,
)

# 지역 결측치는 Unknown으로 표시합니다.
df["region"] = df["region"].fillna("Unknown")

print("\n===== 13. 지역 결측치 처리 =====")
print(
    "지역 결측치:",
    df["region"].isna().sum(),
    "건",
)
print(df["region"].value_counts(dropna=False))


# 수량 결측치는 같은 카테고리의 수량 중앙값으로 채웁니다.
quantity_median_by_row = (
    df.groupby("category")["quantity"]
    .transform("median")
)

df["quantity"] = df["quantity"].fillna(
    quantity_median_by_row
)

# 할인율 결측치는 할인이 없는 것으로 처리합니다.
df["discount"] = df["discount"].fillna(0)


print("\n===== 14. 결측치 처리 결과 =====")
print(df.isna().sum())

print(
    "\n참고: order_date에는 분석용 NaT가 남을 수 있지만, "
    "order_date_display에서는 Unknown으로 처리됐습니다."
)


# 이상치 처리 전 값을 비교용으로 보관합니다.
df["quantity_before_winsor"] = df["quantity"]
df["unit_price_before_winsor"] = df["unit_price"]

print("\n===== 15. 이상치 처리 전 =====")
print("수량 최솟값:", df["quantity"].min())
print("수량 최댓값:", df["quantity"].max())
print("가격 최솟값:", df["unit_price"].min())
print("가격 최댓값:", df["unit_price"].max())


# 수량 이상치를 조정합니다.
quantity_lower, quantity_upper, quantity_outlier_count = (
    winsorize_iqr(
        df,
        "quantity",
    )
)

print("\n===== 16. 수량 이상치 처리 =====")
print(f"수량 하한: {quantity_lower:.2f}")
print(f"수량 상한: {quantity_upper:.2f}")
print("수량 이상치 개수:", quantity_outlier_count)
print("처리 후 수량 최솟값:", df["quantity"].min())
print("처리 후 수량 최댓값:", df["quantity"].max())


# 가격 이상치를 조정합니다.
price_lower, price_upper, price_outlier_count = (
    winsorize_iqr(
        df,
        "unit_price",
    )
)

print("\n===== 17. 가격 이상치 처리 =====")
print(f"가격 하한: {price_lower:.2f}")
print(f"가격 상한: {price_upper:.2f}")
print("가격 이상치 개수:", price_outlier_count)
print("처리 후 가격 최솟값:", df["unit_price"].min())
print("처리 후 가격 최댓값:", df["unit_price"].max())


# 수량이나 가격이 실제로 변경된 행을 찾습니다.
changed_rows = df[
    (df["quantity"] != df["quantity_before_winsor"])
    | (
        df["unit_price"]
        != df["unit_price_before_winsor"]
    )
]

print("\n===== 18. 이상치가 조정된 행 =====")
print("조정된 전체 행 수:", len(changed_rows))

print(
    changed_rows[
        [
            "order_id",
            "category",
            "quantity_before_winsor",
            "quantity",
            "unit_price_before_winsor",
            "unit_price",
        ]
    ].head(20)
)


# 이상치가 남아 있는지 확인합니다.
remaining_quantity_outliers = (
    (df["quantity"] < quantity_lower)
    | (df["quantity"] > quantity_upper)
).sum()

remaining_price_outliers = (
    (df["unit_price"] < price_lower)
    | (df["unit_price"] > price_upper)
).sum()

print("\n===== 19. 이상치 처리 최종 확인 =====")
print(
    "남은 수량 이상치:",
    remaining_quantity_outliers,
)
print(
    "남은 가격 이상치:",
    remaining_price_outliers,
)
print("전체 행 수:", len(df))


# Copy-on-Write를 사용했으므로 원본은 유지되어야 합니다.
print("\n===== 20. 원본 보존 확인 =====")
print("원본 행 수:", len(raw_df))
print("정제 데이터 행 수:", len(df))
print(
    "원본 수량 최댓값:",
    raw_df["quantity"].max(),
)
print(
    "정제 후 수량 최댓값:",
    df["quantity"].max(),
)

print("\n===== 21. 수량 정수화 =====")

df["quantity"] = (
    df["quantity"]
    .round()
    .astype("Int64")
)

print("수량 자료형:", df["quantity"].dtype)
print("수량 최솟값:", df["quantity"].min())
print("수량 최댓값:", df["quantity"].max())


print("\n===== 22. 매출액 계산 =====")

df["sales_amount"] = (
    df["quantity"]
    * df["unit_price"]
    * (1 - df["discount"])
).round(2)

print(
    df[
        [
            "order_id",
            "quantity",
            "unit_price",
            "discount",
            "sales_amount",
        ]
    ].head()
)

print("\n전체 매출액:", f"{df['sales_amount'].sum():,.2f}원")


print("\n===== 23. 연도와 월 컬럼 생성 =====")

df["order_year"] = df["order_date"].dt.year.astype("Int64")
df["order_month"] = df["order_date"].dt.month.astype("Int64")

print(
    df[
        [
            "order_date",
            "order_date_display",
            "order_year",
            "order_month",
        ]
    ].head()
)


print("\n===== 24. 지역·카테고리별 집계 =====")

group_summary = (
    df.groupby(
        ["region", "category"],
        as_index=False,
    )
    .agg(
        order_count=("order_id", "count"),
        total_quantity=("quantity", "sum"),
        average_unit_price=("unit_price", "mean"),
        average_discount=("discount", "mean"),
        total_sales=("sales_amount", "sum"),
    )
    .sort_values(
        "total_sales",
        ascending=False,
    )
)

group_summary["average_unit_price"] = (
    group_summary["average_unit_price"].round(2)
)
group_summary["average_discount"] = (
    group_summary["average_discount"].round(4)
)
group_summary["total_sales"] = (
    group_summary["total_sales"].round(2)
)

print(group_summary.head(15).to_string(index=False))


print("\n===== 25. 지역·카테고리별 매출 피벗 =====")

sales_pivot = df.pivot_table(
    index="region",
    columns="category",
    values="sales_amount",
    aggfunc="sum",
    fill_value=0,
    margins=True,
    margins_name="Total",
).round(2)

print(sales_pivot)


print("\n===== 26. 카테고리 정보 merge =====")

category_info = pd.DataFrame(
    {
        "category": [
            "Beauty",
            "Electronics",
            "Fashion",
            "Food",
            "Home",
        ],
        "category_name_ko": [
            "뷰티",
            "전자제품",
            "패션",
            "식품",
            "생활용품",
        ],
        "category_group": [
            "소비재",
            "내구재",
            "소비재",
            "식품",
            "내구재",
        ],
    }
)

merged_df = df.merge(
    category_info,
    on="category",
    how="left",
    validate="many_to_one",
)

print(
    merged_df[
        [
            "order_id",
            "category",
            "category_name_ko",
            "category_group",
            "sales_amount",
        ]
    ].head()
)

print(
    "병합 후 카테고리명 결측치:",
    merged_df["category_name_ko"].isna().sum(),
)


print("\n===== 27. 카테고리 그룹별 매출 =====")

category_group_summary = (
    merged_df.groupby(
        "category_group",
        as_index=False,
    )
    .agg(
        order_count=("order_id", "count"),
        total_quantity=("quantity", "sum"),
        total_sales=("sales_amount", "sum"),
    )
    .sort_values(
        "total_sales",
        ascending=False,
    )
)

category_group_summary["total_sales"] = (
    category_group_summary["total_sales"].round(2)
)

print(category_group_summary.to_string(index=False))


print("\n===== 28. Copy-on-Write 확인 =====")

beauty_rows = df[df["category"] == "Beauty"]
original_discount = beauty_rows["discount"].iloc[0]

beauty_rows.loc[:, "discount"] = 0.99

source_discount = df.loc[
    df["category"] == "Beauty",
    "discount",
].iloc[0]

print("부분 데이터 수정 전 할인율:", original_discount)
print("부분 데이터 수정 후 값:", beauty_rows["discount"].iloc[0])
print("원본 df의 할인율:", source_discount)

if source_discount == original_discount:
    print("Copy-on-Write 정상: 원본 df가 변경되지 않았습니다.")
else:
    print("주의: 원본 df가 변경됐습니다.")


print("\n===== 29. 정제 전후 비교 =====")

print("원본 행 수:", len(raw_df))
print("정제 후 행 수:", len(merged_df))

print("\n원본 결측치:")
print(raw_df.isna().sum())

print("\n정제 후 주요 컬럼 결측치:")
print(
    merged_df[
        [
            "region",
            "quantity",
            "unit_price",
            "discount",
            "order_date_display",
        ]
    ].isna().sum()
)

print("\n원본 수량 최댓값:", raw_df["quantity"].max())
print("정제 후 수량 최댓값:", merged_df["quantity"].max())

print("\n원본 가격 최솟값:", raw_df["unit_price"].min())
print("정제 후 가격 최솟값:", merged_df["unit_price"].min())


print("\n===== 30. 결과 파일 저장 =====")

OUTPUT_DIR = Path(__file__).parent / "output"
OUTPUT_DIR.mkdir(
    parents=True,
    exist_ok=True,
)

CLEANED_FILE = OUTPUT_DIR / "sales_cleaned.csv"
GROUP_FILE = OUTPUT_DIR / "sales_group_summary.csv"
PIVOT_FILE = OUTPUT_DIR / "sales_pivot.csv"
CATEGORY_GROUP_FILE = (
    OUTPUT_DIR / "category_group_summary.csv"
)

merged_df.to_csv(
    CLEANED_FILE,
    index=False,
    encoding="utf-8-sig",
)

group_summary.to_csv(
    GROUP_FILE,
    index=False,
    encoding="utf-8-sig",
)

sales_pivot.to_csv(
    PIVOT_FILE,
    encoding="utf-8-sig",
)

category_group_summary.to_csv(
    CATEGORY_GROUP_FILE,
    index=False,
    encoding="utf-8-sig",
)

print("정제 데이터:", CLEANED_FILE)
print("지역·카테고리 요약:", GROUP_FILE)
print("피벗 테이블:", PIVOT_FILE)
print("카테고리 그룹 요약:", CATEGORY_GROUP_FILE)


print("\n===== 31. 저장 파일 검증 =====")

saved_df = pd.read_csv(CLEANED_FILE)

print("저장된 행 수:", len(saved_df))
print("저장된 열 수:", len(saved_df.columns))

if len(saved_df) == len(merged_df):
    print("저장 검증 성공: 행 개수가 같습니다.")
else:
    print("주의: 저장 전후 행 개수가 다릅니다.")