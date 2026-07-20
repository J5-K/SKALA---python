"""ETL의 Transform 단계에서 사용할 데이터 검증 규칙입니다."""

from pydantic import BaseModel, Field, field_validator


class Product(BaseModel):
    """외부 API에서 받아오는 상품 한 건의 모양입니다."""

    id: int = Field(gt=0)
    name: str = Field(min_length=1)
    category: str = Field(min_length=1)
    price: float = Field(gt=0)

    @field_validator("category")
    @classmethod
    def normalize_category(cls, value: str) -> str:
        # ' FOOD '처럼 들어와도 뒤에서 항상 'food'로 사용할 수 있게 정리합니다.
        cleaned = value.strip().lower()
        if not cleaned:
            raise ValueError("카테고리는 비어 있을 수 없습니다")
        return cleaned
