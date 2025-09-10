from __future__ import annotations

import os
from typing import List

from ..models import AIReportRequest, Requirement


def _build_prompt(payload: AIReportRequest) -> str:
    b = payload.business
    req_lines = []
    for r in payload.matched:
        req_lines.append(f"- {r.title}: {r.description}")

    lang = payload.language or "he"
    if lang.lower().startswith("he"):
        header = (
            "אתה מסייע רישוי עסקים. צור דוח ברור, מסודר ופרקטי בעברית, המותאם לעסק: "
            f"שטח {b.area_sqm} מ""ר, {b.seats} מקומות ישיבה, שימוש בגז: {b.uses_gas}, מגיש בשר: {b.serves_meat}, משלוחים: {b.offers_delivery}.\n"  # noqa: E501
            "ארגן לפי קטגוריות, סדר עדיפויות, והמלצות פעולה. הימנע משפה משפטית.\n"
        )
    else:
        header = (
            "You are a licensing assistant. Create a clear, structured, and actionable report tailored to the business: "
            f"area {b.area_sqm} sqm, {b.seats} seats, uses gas: {b.uses_gas}, serves meat: {b.serves_meat}, delivery: {b.offers_delivery}.\n"  # noqa: E501
            "Organize by categories, priorities, and action items. Avoid legalese.\n"
        )

    return header + "\n".join(req_lines)


def generate_ai_report(payload: AIReportRequest) -> str:
    # If OPENAI_API_KEY is available and openai SDK installed, use it. Otherwise, fallback.
    prompt = _build_prompt(payload)
    api_key = os.getenv("OPENAI_API_KEY")
    if api_key:
        try:
            # OpenAI SDK v1.x (optional dependency)
            from openai import OpenAI  # type: ignore

            client = OpenAI(api_key=api_key)
            completion = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You write clear, structured licensing reports."},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.2,
                max_tokens=900,
            )
            content = completion.choices[0].message.content or ""
            if isinstance(content, list):
                # Some SDK returns content as list of parts
                content = "".join([p.get("text", "") if isinstance(p, dict) else str(p) for p in content])
            if content:
                return content
        except Exception:
            # Fail silent to fallback
            pass
    lines: List[str] = [
        "דוח התאמה מותאם אישית", 
        "======================", 
        "", 
        "תקציר מנהלים:",
    ]

    # Simple summary
    b = payload.business
    lines.append(
        f"העסק נמדד בשטח {b.area_sqm} מ" + '"' + f"ר עם {b.seats} מקומות. שימוש בגז: {b.uses_gas}. בשר: {b.serves_meat}. משלוחים: {b.offers_delivery}."
    )
    lines.append("")
    lines.append("דרישות עיקריות:")
    for r in payload.matched[:10]:
        lines.append(f"- {r.title}")
    if len(payload.matched) > 10:
        lines.append(f"ועוד {len(payload.matched) - 10} דרישות נוספות…")

    lines.append("")
    lines.append("המלצות פעולה קריטיות (14 הימים הקרובים):")
    for r in payload.matched[:5]:
        lines.append(f"1. אשר/הגש: {r.title}")

    lines.append("")
    lines.append("נספח: תקציר דרישות")
    for r in payload.matched[:20]:
        lines.append(f"- {r.title}: {r.description[:180]}…")

    # If OPENAI_API_KEY present, optionally enrich (placeholder to keep no-op by default)
    # This is where you'd call an external API.
    return "\n".join(lines)


