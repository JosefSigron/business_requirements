import argparse
from .services.parser import parse_docx_and_save


def main() -> None:
    parser = argparse.ArgumentParser(description="Parse DOCX to JSON/CSV")
    parser.add_argument("docx_path", help="Path to 18-07-2022_4.2A.docx")
    args = parser.parse_args()
    items = parse_docx_and_save(args.docx_path)
    print(f"Parsed {len(items)} requirements. Saved to backend/data/processed/")


if __name__ == "__main__":
    main()


