"""종합실습 3에서 공유하는 변경 불가능한 설정."""

from dataclasses import dataclass
from pathlib import Path


BASE_DIR = Path(__file__).parent


@dataclass(frozen=True)
class Config:
    title: str = "매출 분석 자동 리포트"
    data_path: Path = BASE_DIR / "sales_raw.csv"
    template_dir: Path = BASE_DIR / "templates"
    output_dir: Path = BASE_DIR / "output"
    top_n: int = 5


CONFIG = Config()
