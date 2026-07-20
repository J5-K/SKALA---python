import json
from pathlib import Path
from pydantic import BaseModel,BaseModel, Field, field_validator, ValidationError
from datetime import date
from typing import Literal

DATA_PATH = Path(__file__).parent / "api_response.json"

with DATA_PATH.open(encoding="utf-8") as file:
    data = json.load(file)

#안쪽 상자
class Profile(BaseModel):
    country: Literal["KR", "US", "JP", "DE"]
    tier: Literal["free", "pro", "enterprise"]
    score: float = Field(ge=0, le=100)

#바깥 상자
class User(BaseModel):
    id: int = Field(gt=0)
    username: str = Field(min_length=1)
    email: str
    age: int = Field(ge=0, le=120)
    is_active: bool
    signup_date: date
    profile: Profile
    tags: list[str]

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str) -> str:
        value = value.strip().lower()

        if "@" not in value:
            raise ValueError("올바른 이메일 형식이 아닙니다")

        return value

some_user = data["results"][0]     #id=29 사용자는 profile.score가 150.0이므로 le=100 규칙에 걸림
user = User.model_validate(some_user)

print(user)

valid_users = []
invalid_users = []

for index, row in enumerate(data["results"], start=1):
    try:
        user = User.model_validate(row)
        valid_users.append(user)

    except ValidationError as error:
        invalid_users.append(
            {
                "index": index,
                "id": row.get("id"),
                "errors": error.errors(include_url=False),
            }
        )

print(f"전체: {len(data['results'])}건")
print(f"유효: {len(valid_users)}건")
print(f"오염: {len(invalid_users)}건")

print(f"{'행':<4}{'필드':<12}{'사유'}")
for item in invalid_users:
    for err in item['errors']:
        field = '.'.join(str(x) for x in err['loc'])   # 중첩 경로 표시
        print(f"{item['index']:<4}{field:<12}{err['msg']}")
