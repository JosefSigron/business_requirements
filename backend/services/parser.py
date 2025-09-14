from __future__ import annotations

from pathlib import Path
from typing import List, Dict, Optional
import json
import re

from bidi.algorithm import get_display

from ..models import Requirement, SectionNode


DATA_DIR = Path(__file__).parent.parent / "data" / "processed"
DATA_DIR.mkdir(parents=True, exist_ok=True)
JSON_PATH = DATA_DIR / "requirements.json"
STRUCTURE_PATH = DATA_DIR / "structure.json"


def _normalize_whitespace(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


# Note: Do not reorder text at parse time. Store logical (original) text.
# Rendering should be handled by the client (e.g., dir="rtl" in HTML/CSS).


def _extract_requirements_from_txt(txt_path: str) -> List[Requirement]:
    text = Path(txt_path).read_text(encoding="utf-8-sig", errors="ignore")
    lines = [l.strip() for l in text.splitlines()]
    items: List[Requirement] = []
    counter = 0
    for raw in lines:
        raw = _normalize_whitespace(raw)
        if not raw:
            continue
        counter += 1
        title_text = " ".join(raw.split(" ")[:8])
        lower = raw.lower()
        offers_delivery = any(k in raw for k in ["משלוח", "שליח", "משלוחים"]) or "delivery" in lower
        serves_meat = any(k in raw for k in ["בשר", "מזון מן החי"]) or "meat" in lower
        requires_gas = any(k in raw for k in ["גז"]) or "gas" in lower
        area_min = None
        area_max = None
        seats_min = None
        seats_max = None
        for match in re.finditer(r"(\d{1,4})\s*(?:מ\"ר|sqm)", raw):
            value = float(match.group(1))
            if area_min is None or value < area_min:
                area_min = value
            if area_max is None or value > area_max:
                area_max = value
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


def parse_txt_and_save(txt_path: str) -> List[Requirement]:
    requirements = _extract_requirements_from_txt(txt_path)

    # Save JSON
    with JSON_PATH.open("w", encoding="utf-8") as f:
        json.dump([r.dict() for r in requirements], f, ensure_ascii=False, indent=2)

    return requirements


def load_requirements() -> List[Requirement]:
    if not JSON_PATH.exists():
        return []
    data = json.loads(JSON_PATH.read_text(encoding="utf-8"))
    return [Requirement(**row) for row in data]


SECTION_RE = re.compile(r"^(\d+(?:\.\d+){1,5})\.?\s+(.+)$")
INLINE_L3 = re.compile(r"(\d+(?:\.\d+){1,5})\.?\s+(.+)")
ANNEX4_START = "נספחים"
ANNEX5_START = "נספח 1 (לנספח א')"
ANNEX5_END = "נספח  ג' - טופס ביקורת תברואית בבית אוכל"
CHAPTER1_RE = re.compile(r"^פרק\s*1\b")
CHAPTER5_RE = re.compile(r"^פרק\s*5\b")
ANNEX5_END_RE = re.compile(r"^נספח\s*ג['\"׳]?\s*-\s*טופס ביקורת תברואית בבית אוכל")


def _split_inline_headers(line: str) -> List[str]:
    parts: List[str] = []
    # Find all occurrences of header tokens anywhere in the line
    matches = list(re.finditer(r"(\d+(?:\.\d+){1,4})\.?\s+", line))
    if not matches:
        return [line]
    for idx, m in enumerate(matches):
        start = m.start(1)
        key = m.group(1)
        body_start = m.end()
        body_end = matches[idx + 1].start(1) if idx + 1 < len(matches) else len(line)
        body_text = line[body_start:body_end].strip()
        parts.append(f"{key} {body_text}")
    return parts


def _extract_section_tree_from_lines(lines: List[str]) -> List[SectionNode]:
    roots: Dict[str, SectionNode] = {}
    level1_stack: Dict[str, SectionNode] = {}
    level2_stack: Dict[str, SectionNode] = {}
    level3_stack: Dict[str, SectionNode] = {}
    level4_stack: Dict[str, SectionNode] = {}
    level5_stack: Dict[str, SectionNode] = {}
    context: Optional[str] = None  # None / annex4 / annex5
    annex4_level = None  # "4.1", "4.2", "4.3"
    annex5_level = None  # "5.1", "5.2", "5.3"

    def parse_line(text: str) -> Optional[tuple[str, str]]:
        m = SECTION_RE.match(text)
        if not m:
            return None
        return m.group(1), m.group(2)

    def infer_title(body: str) -> str:
        words = body.split(" ")
        return " ".join(words[:8])

    tree: List[SectionNode] = []
    last_node: Optional[SectionNode] = None
    i = 0
    seen_chapter1 = False
    while i < len(lines):
        raw_line = lines[i]
        raw = _normalize_whitespace(raw_line)
        if not raw:
            i += 1
            continue
        # Skip everything until Chapter 1
        if not seen_chapter1:
            if CHAPTER1_RE.search(raw):
                seen_chapter1 = True
            else:
                i += 1
                continue
        # Context transitions
        if raw.startswith(ANNEX4_START):
            context = "annex4"
            annex4_level = "4.1"
            annex5_level = None
        elif raw.startswith(ANNEX5_START):
            context = "annex5"
            annex5_level = "5.1"
        elif ANNEX5_END_RE.search(raw):
            # end annex5 block, ignore all lines until CHAPTER5_RE appears
            context = "annex4"
            # fast-forward until we meet Chapter 5
            j = i + 1
            skipped = False
            while j < len(lines):
                nxt = _normalize_whitespace(lines[j])
                if CHAPTER5_RE.search(nxt):
                    i = j  # next loop will process chapter 5 line
                    skipped = True
                    break
                j += 1
            if skipped:
                continue
        elif CHAPTER5_RE.search(raw):
            # back to normal numbering after chapter 5
            context = None

        # If a line contains multiple headers inline, split into separate synthetic lines
        if SECTION_RE.search(raw) and not raw.startswith(tuple([m.group(1) for m in SECTION_RE.finditer(raw)])):
            # conservative: always split into header segments and process the first now
            segs = _split_inline_headers(raw)
            # replace current line with the first segment, insert the rest to be processed next
            lines[i] = segs[0]
            for off, seg in enumerate(segs[1:], start=1):
                lines.insert(i + off, seg)
            raw = lines[i]

        parsed = parse_line(raw)
        if not parsed:
            # append free text to last node if exists
            if last_node is not None:
                m_tail = re.search(r"פרק\s+\d+|נספח(?:ים)?", raw)
                tail = raw[:m_tail.start()] if m_tail else raw
                # Truncate at enumeration/bullet if present
                m_enum2 = re.search(r"(?:^|\s)([א-ת]\.\s|\d+\.\s|\(\d{1,2}\)\s)", tail)
                if m_enum2:
                    tail = tail[:m_enum2.start()]
                tail = tail.strip()
                if tail:
                    if last_node.id == "8.5.9":
                        combined = (last_node.text + " " + tail).strip()
                        mfs = re.search(r"[.!?]", combined)
                        last_node.text = (combined[: mfs.end()].strip() if mfs else combined)
                    else:
                        last_node.text = (last_node.text + " " + tail).strip()
            i += 1
            continue
        key, body = parsed
        # determine level by number of dots in key (support up to 6 levels)
        dot_count = key.count('.')
        level = min(dot_count + 1, 6)
        # In normal context, ignore level-1 entries entirely (we only care about x.x and x.x.x)
        if context is None and level == 1:
            i += 1
            continue
        # guard: if body contains any nested level tokens, split them out to new lines (up to level 6)
        inner_matches = list(re.finditer(r"(\d+\.\d+(?:\.\d+){0,4})\.?\s+", body))
        if inner_matches:
            start_idx = 0
            for idx, m in enumerate(inner_matches):
                # everything before first inner header stays as current body
                if idx == 0:
                    body_before = body[:m.start()].strip()
                    body = body_before
                # push subsequent headers as new lines after current index
                next_key = m.group(1)
                end_pos = inner_matches[idx + 1].start() if idx + 1 < len(inner_matches) else len(body)
                seg_body = body[m.end():end_pos].strip()
                lines.insert(i + 1 + idx, f"{next_key} {seg_body}")

        # heuristics
        lower = body.lower()
        offers_delivery = any(k in body for k in ["משלוח", "שליח", "משלוחים"]) or "delivery" in lower
        serves_meat = any(k in body for k in ["בשר", "מזון מן החי"]) or "meat" in lower
        requires_gas = any(k in body for k in ["גז"]) or "gas" in lower

        # Derive area bounds from Hebrew comparative phrases
        def derive_area_bounds(text: str) -> tuple[float | None, float | None]:
            t = text
            # Must reference area notion
            if not re.search(r"(?<!\w)(שטח|שטחים|מ\"ר|מ'|מ׳)(?!\w)", t):
                return None, None
            min_b: float | None = None
            max_b: float | None = None

            sep = r'[-\u2013\u2014\u05F3"\u05F4\u05BE]?\s*'
            gt_patterns = [
                rf"(?<!\w)מעל\s*{sep}(\d{{1,4}})(?!\w)",
                rf"(?<!\w)גדול(?:ה)?\s*מ\s*{sep}(\d{{1,4}})(?!\w)",
                rf"(?<!\w)יותר\s*מ\s*{sep}(\d{{1,4}})(?!\w)",
            ]
            lt_patterns = [
                rf"(?<!\w)מתחת(?:\s*ל)?\s*{sep}(\d{{1,4}})(?!\w)",
                rf"(?<!\w)קטן(?:ה)?\s*מ\s*{sep}(\d{{1,4}})(?!\w)",
                rf"(?<!\w)פחות\s*מ\s*{sep}(\d{{1,4}})(?!\w)",
            ]
            ge_patterns = [
                rf"(?<!\w)לפחות\s*{sep}(\d{{1,4}})(?!\w)",
                rf"(?<!\w)לא\s+פחות\s+מ\s*{sep}(\d{{1,4}})(?!\w)",
                rf"(?<!\w)מינימום\s*{sep}(\d{{1,4}})(?!\w)",
            ]
            le_patterns = [
                rf"(?<!\w)עד\s*{sep}(\d{{1,4}})(?!\w)",
                rf"(?<!\w)לא\s+יותר\s+מ\s*{sep}(\d{{1,4}})(?!\w)",
                rf"(?<!\w)מקסימום\s*{sep}(\d{{1,4}})(?!\w)",
            ]

            # between X to Y
            between = re.search(r"(?<!\w)בין\s*(\d{1,4})\s*ל\s*(\d{1,4})(?!\w)", t)
            if between:
                a = int(between.group(1)); b2 = int(between.group(2))
                return float(min(a, b2)), float(max(a, b2))

            def scan(patterns, set_min=False, set_max=False):
                nonlocal min_b, max_b
                for p in patterns:
                    m = re.search(p, t)
                    if m:
                        try:
                            n = float(m.group(1))
                            if set_min:
                                min_b = n if min_b is None else max(min_b, n)
                            if set_max:
                                max_b = n if max_b is None else min(max_b, n)
                        except Exception:
                            continue

            scan(gt_patterns, set_min=True)
            scan(ge_patterns, set_min=True)
            scan(lt_patterns, set_max=True)
            scan(le_patterns, set_max=True)
            return min_b, max_b

        min_area_sqm, max_area_sqm = derive_area_bounds(body)

        # Seats simple extraction (keep current heuristic; do not force bounds unless explicit words present)
        seats_vals = [int(m.group(1)) for m in re.finditer(r"(\d{1,4})\s*(?:מקומות|מושבים|seats)", body)]
        min_seats = min(seats_vals) if seats_vals else None
        max_seats = max(seats_vals) if seats_vals else None
        # Remove chapter/annex markers and everything after (e.g., " פרק 6 ..." or " נספח ...")
        m_trunc = re.search(r"פרק\s+\d+|נספח(?:ים)?", body)
        display_body = (body[:m_trunc.start()] if m_trunc else body).rstrip()
        # Further truncate at the first enumeration/bullet token (e.g., "א.", "1.", or "(1)")
        m_enum = re.search(r"(?:^|\s)([א-ת]\.\s|\d+\.\s|\(\d{1,2}\)\s)", display_body)
        if m_enum:
            display_body = display_body[:m_enum.start()].rstrip()
        # Specific correction: for 8.5.9 keep only the first sentence
        if key == "8.5.9":
            m_first_sentence = re.search(r"[.!?]", display_body)
            if m_first_sentence:
                display_body = display_body[: m_first_sentence.end()].strip()
        # Improve display for enumerations like (1), (2) by breaking lines
        display_body = re.sub(r"(?<!^)\s*\((\d{1,2})\)\s*", r"\n(\1) ", display_body)
        # Derive a short title from the trimmed display body
        def make_title(t: str) -> str:
            t0 = t.strip()
            # use first line only for title
            line = t0.split("\n", 1)[0]
            words = line.split(" ")
            return " ".join([w for w in words if w][:8])
        title_text = make_title(display_body)

        # set annex group level label by depth
        if context == "annex4":
            group_label = "4.2" if level == 2 else ("4.3" if level == 3 else "4.1")
        elif context == "annex5":
            group_label = "5.2" if level == 2 else ("5.3" if level == 3 else "5.1")
        else:
            group_label = None

        node = SectionNode(
            id=key,
            level=level,
            title=title_text,
            text=display_body,
            context=context,
            group_level=group_label,
            min_area_sqm=min_area_sqm,
            max_area_sqm=max_area_sqm,
            min_seats=min_seats,
            max_seats=max_seats,
            requires_gas=requires_gas or None,
            serves_meat=serves_meat or None,
            offers_delivery=offers_delivery or None,
            children=[],
        )

        if level == 1:
            roots[key] = node
            level1_stack[key] = node
            tree.append(node)
        elif level == 2:
            parent_key = key.rsplit(".", 1)[0]
            parent = level1_stack.get(parent_key)
            if parent is None:
                # orphan; treat as root
                tree.append(node)
                # Ensure orphan level-2 nodes are still tracked as potential parents
                level2_stack[key] = node
            else:
                parent.children.append(node)
                level2_stack[key] = node
        elif level == 3:
            parent_key = key.rsplit(".", 1)[0]
            parent = level2_stack.get(parent_key)
            if parent is None:
                # attach to nearest level 1 if possible
                parent_key_l1 = key.split(".")[0]
                parent_l1 = level1_stack.get(parent_key_l1)
                if parent_l1 is not None:
                    parent_l1.children.append(node)
                else:
                    tree.append(node)
            else:
                parent.children.append(node)
            level3_stack[key] = node
        elif level == 4:
            parent_key = key.rsplit(".", 1)[0]
            parent = level3_stack.get(parent_key)
            if parent is None:
                # attach to nearest level 2 if possible
                parent_key_l2 = ".".join(key.split(".")[:2])
                parent_l2 = level2_stack.get(parent_key_l2)
                if parent_l2 is not None:
                    parent_l2.children.append(node)
                else:
                    tree.append(node)
            else:
                parent.children.append(node)
            level4_stack[key] = node
        elif level == 5:
            parent_key = key.rsplit(".", 1)[0]
            parent = level4_stack.get(parent_key)
            if parent is None:
                # attach to nearest level 3 if possible
                parent_key_l3 = ".".join(key.split(".")[:3])
                parent_l3 = level3_stack.get(parent_key_l3)
                if parent_l3 is not None:
                    parent_l3.children.append(node)
                else:
                    tree.append(node)
            else:
                parent.children.append(node)
            level5_stack[key] = node
        else:  # level 6
            parent_key = key.rsplit(".", 1)[0]
            parent = level5_stack.get(parent_key)
            if parent is None:
                # fallback to nearest level 4 if available
                parent_key_l4 = ".".join(key.split(".")[:4])
                parent_l4 = level4_stack.get(parent_key_l4)
                if parent_l4 is not None:
                    parent_l4.children.append(node)
                else:
                    tree.append(node)
            else:
                parent.children.append(node)
        last_node = node
        i += 1

    # Sort tree and children by numeric id order
    def id_key(s: str) -> List[int]:
        try:
            return [int(x) for x in s.split('.')]
        except Exception:
            return [10**9]

    def sort_nodes(nodes: List[SectionNode]) -> None:
        nodes.sort(key=lambda n: id_key(n.id))
        for n in nodes:
            sort_nodes(n.children)

    sort_nodes(tree)

    # Reorder groups: context None first, then annex4, then annex5
    def context_key(n: SectionNode) -> int:
        if not n.context:
            return 0
        if n.context == "annex4":
            return 1
        if n.context == "annex5":
            return 2
        return 3

    tree.sort(key=lambda n: (context_key(n), [int(x) for x in n.id.split('.')]))
    return tree


def parse_structure_and_save(file_path: str) -> List[SectionNode]:
    path = Path(file_path)
    lines: List[str] = []
    # TXT-only support
    text = path.read_text(encoding="utf-8-sig", errors="ignore")
    lines = text.splitlines()
    tree = _extract_section_tree_from_lines(lines)
    with STRUCTURE_PATH.open("w", encoding="utf-8") as f:
        json.dump([n.dict() for n in tree], f, ensure_ascii=False, indent=2)
    return tree


def load_structure() -> List[SectionNode]:
    if not STRUCTURE_PATH.exists():
        return []
    data = json.loads(STRUCTURE_PATH.read_text(encoding="utf-8"))
    return [SectionNode(**row) for row in data]


