import json
from pathlib import Path


DATA_FILE = Path(__file__).parent / "api_response.json"


def load_json(file_path: Path):
    """JSON 파일을 읽어서 파이썬 데이터로 반환합니다."""
    with file_path.open("r", encoding="utf-8-sig") as file:
        return json.load(file)


def main() -> None:
    print("데이터 파일:", DATA_FILE)
    print("파일 존재 여부:", DATA_FILE.exists())

    if not DATA_FILE.exists():
        print("오류: api_response.json 파일을 찾지 못했습니다.")
        return

    raw_data = load_json(DATA_FILE)
    data = raw_data["results"]

    print("\n===== 기본 구조 확인 =====")
    print("최상위 자료형:", type(data).__name__)

    if isinstance(data, list):
        print("전체 데이터 수:", len(data))

        print("\n===== 첫 번째 데이터 =====")
        print(json.dumps(data[0], ensure_ascii=False, indent=2))

        print("\n===== 첫 번째 데이터의 열 이름 =====")
        print(data[0].keys())

    elif isinstance(data, dict):
        print("최상위 키:", data.keys())

        print("\n===== 전체 내용 일부 =====")
        print(json.dumps(data, ensure_ascii=False, indent=2)[:3000])

    else:
        print("예상하지 못한 JSON 구조입니다.")


if __name__ == "__main__":
    main()