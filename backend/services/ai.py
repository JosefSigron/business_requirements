from __future__ import annotations

import os
from typing import List

from ..models import AIReportStructureRequest, SectionNode


def _extract_text_from_choice(choice) -> str:
    try:
        msg = choice.message
        content = getattr(msg, "content", None)
        if isinstance(content, str):
            return content.strip()
        if isinstance(content, list):
            parts: List[str] = []
            for p in content:
                # Support dict-like or object-like content parts
                if isinstance(p, dict):
                    parts.append(p.get("text") or p.get("input_text") or "")
                else:
                    parts.append(getattr(p, "text", "") or getattr(p, "input_text", ""))
            text = "".join([t for t in parts if t]).strip()
            if text:
                return text
        # Fallback: some SDKs put text directly on choice
        text_direct = getattr(choice, "text", None)
        if isinstance(text_direct, str) and text_direct.strip():
            return text_direct.strip()
    except Exception:
        pass
    return ""


# Removed flat requirements prompt; structure-based prompt used instead


def _complete_with_openai(prompt: str) -> str:
    """Call OpenAI (Responses API) and return the text. Raise on any failure."""
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is not set")
    try:
        from openai import OpenAI  # type: ignore

        client = OpenAI(api_key=api_key)
        response = client.responses.create(
            model="gpt-5",
            input=[
                {
                    "role": "system",
                    "content": [
                        {
                            "type": "input_text",
                            "text": "אתה יועץ רישוי עסקים. צור דוח מקצועי וברור בעברית, מותאם לעסק, עם קטגוריות, עדיפויות והמלצות פעולה. הימנע משפה משפטית; השתמש במונחים עסקיים פשוטים וברורים. השב בעברית בלבד.",
                        }
                    ],
                },
                {"role": "user", "content": [{"type": "input_text", "text": prompt}]},
            ],
        )

        # Prefer the SDK helper if available
        text: str = getattr(response, "output_text", "") or ""
        if not text:
            # Fallback: traverse response.output content parts
            parts: List[str] = []
            output = getattr(response, "output", None)
            if output:
                for item in output:
                    content = getattr(item, "content", None) or []
                    for c in content:
                        t = getattr(c, "text", None)
                        if t is not None:
                            val = getattr(t, "value", None)
                            if isinstance(val, str):
                                parts.append(val)
            text = "".join(parts).strip()
        if not text:
            raise RuntimeError("OpenAI returned empty response text")
        return text
    except Exception as e:
        raise RuntimeError(f"OpenAI call failed: {e}")


# Removed flat-report generation; use generate_ai_report_from_nodes


def _flatten_nodes_depth_first(nodes: List[SectionNode]) -> List[SectionNode]:
    flat: List[SectionNode] = []
    def walk(node: SectionNode) -> None:
        flat.append(node)
        for child in node.children or []:
            walk(child)
    for node in nodes:
        walk(node)
    return flat


def _build_prompt_from_nodes(payload: AIReportStructureRequest) -> str:
    b = payload.business
    parts: List[str] = []
    # Include all descendants, not just the top-level matched nodes
    for n in _flatten_nodes_depth_first(payload.nodes):
        label = n.title or n.id
        try:
            indent = "  " * max((n.level or 1) - 1, 0)
        except Exception:
            indent = ""
        parts.append(f"{indent}- [{n.id}] {label}: {n.text}")
    lang = payload.language or "he"
    if lang.lower().startswith("he"):
        header = (
            f'פרטי העסק: שטח {b.area_sqm} מ"ר, {b.seats} מקומות ישיבה, גז: {b.uses_gas}, בשר: {b.serves_meat}, משלוחים: {b.offers_delivery}.\n\n'
        )
        guidelines = (
            "הנחיות הפקה:\n"
            "- כתיבה בעברית ברורה ונגישה (ללא שפה משפטית).\n"
            "- ארגון תוכן לקטגוריות עם עדיפויות (גבוהה/בינונית/נמוכה) ונימוק.\n"
            "- המלצות פעולה קונקרטיות (צעדים, אחריות, תלות).\n\n"
        )
        template = (
            "תבנית נדרשת:\n"
            "1) סיכום מנהלים קצר.\n"
            "2) דרישות לפי קטגוריות עם עדיפויות ורציונל.\n"
            "3) תוכנית פעולה (צ'קליסט).\n"
            "4) סיכונים/הערות.\n"
            "5) מידע חסר/הנחות.\n\n"
        )
        data_block = "סעיפים למימוש/ניתוח:\n" + "\n".join(parts)
        return header + guidelines + template + data_block
    else:
        header = (
            f"Business: area {b.area_sqm} sqm, {b.seats} seats, gas: {b.uses_gas}, meat: {b.serves_meat}, delivery: {b.offers_delivery}.\n\n"
        )
        guidelines = (
            "Guidelines:\n"
            "- Clear business language; avoid legalese.\n"
            "- Categories with priorities and rationale.\n"
            "- Actionable plan (checklist).\n\n"
        )
        template = (
            "Required format:\n"
            "1) Executive summary.\n"
            "2) Requirements by category with priorities.\n"
            "3) Action plan checklist.\n"
            "4) Risks/Notes.\n"
            "5) Missing info/Assumptions.\n\n"
        )
        data_block = "Sections to analyze:\n" + "\n".join(parts)
        return header + guidelines + template + data_block


def generate_ai_report_from_nodes(payload: AIReportStructureRequest) -> str:
    prompt = _build_prompt_from_nodes(payload)
    return _complete_with_openai(prompt)


