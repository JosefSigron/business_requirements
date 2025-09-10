from __future__ import annotations

from pathlib import Path
from typing import List
import json
import re

from docx import Document

from ..models import Requirement


DATA_DIR = Path(__file__).parent.parent / "data" / "processed"
DATA_DIR.mkdir(parents=True, exist_ok=True)
JSON_PATH = DATA_DIR / "requirements.json"
CSV_PATH = DATA_DIR / "requirements.csv"


def _normalize_whitespace(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def _extract_requirements_from_docx(docx_path: str) -> List[Requirement]:
    doc = Document(docx_path)
    items: List[Requirement] = []
    counter = 0

    # Heuristic: treat each non-empty paragraph as a potential requirement row
    # Attempt to parse coarse attributes using simple keyword heuristics
    for para in doc.paragraphs:
        raw = _normalize_whitespace(para.text)
        if not raw:
            continue
        counter += 1
        title = raw.split(" ")[:8]
        title_text = " ".join(title)

        lower = raw.lower()
        # naive heuristics based on Hebrew/keywords
        offers_delivery = any(k in raw for k in ["משלוח", "שליח", "משלוחים"]) or "delivery" in lower
        serves_meat = any(k in raw for k in ["בשר", "מזון מן החי"]) or "meat" in lower
        requires_gas = any(k in raw for k in ["גז"]) or "gas" in lower

        # extract simple numeric ranges if present (sqm or seats), very heuristic
        area_min = None
        area_max = None
        seats_min = None
        seats_max = None

        # Look for patterns like 50 מ"ר or 50 sqm
        for match in re.finditer(r"(\d{1,4})\s*(?:מ\"ר|sqm)", raw):
            value = float(match.group(1))
            if area_min is None or value < area_min:
                area_min = value
            if area_max is None or value > area_max:
                area_max = value

        # Look for seat counts like 100 מקומות / מושבים / seats
        for match in re.finditer(r"(\d{1,4})\s*(?:מקומות|מושבים|seats)", raw):
            value_i = int(match.group(1))
            if seats_min is None or value_i < seats_min:
                seats_min = value_i
            if seats_max is None or value_i > seats_max:
                seats_max = value_i

        items.append(
            Requirement(
                id=f"req-{counter}",
                title=title_text,
                description=raw,
                min_area_sqm=area_min,
                max_area_sqm=area_max,
                min_seats=seats_min,
                max_seats=seats_max,
                requires_gas=requires_gas or None,
                serves_meat=serves_meat or None,
                offers_delivery=offers_delivery or None,
                category=None,
            )
        )
    return items


def parse_docx_and_save(docx_path: str) -> List[Requirement]:
    requirements = _extract_requirements_from_docx(docx_path)

    # Save JSON
    with JSON_PATH.open("w", encoding="utf-8") as f:
        json.dump([r.dict() for r in requirements], f, ensure_ascii=False, indent=2)

    # Save CSV
    try:
        import csv

        with CSV_PATH.open("w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(
                f,
                fieldnames=list(Requirement.model_fields.keys()),
            )
            writer.writeheader()
            for r in requirements:
                writer.writerow(r.dict())
    except Exception:
        # CSV is best-effort
        pass

    return requirements


def load_requirements() -> List[Requirement]:
    if not JSON_PATH.exists():
        return []
    data = json.loads(JSON_PATH.read_text(encoding="utf-8"))
    return [Requirement(**row) for row in data]


