"""Sales Pulse 프로젝트 설정."""

from dataclasses import dataclass
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent


@dataclass(frozen=True)
class Config:
    title: str = "Sales Pulse - 매출 건강검진 리포트"
    data_path: Path = BASE_DIR.parent / "Total3" / "sales_raw.csv"
    template_dir: Path = BASE_DIR / "templates"
    output_dir: Path = BASE_DIR / "output"
    comparison_days: int = 30
    anomaly_z_score: float = 2.0


CONFIG = Config()
