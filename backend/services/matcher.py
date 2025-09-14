from typing import List, Dict

from ..models import BusinessInput, SectionNode
import re


def _within_range(value, min_value, max_value) -> bool:
    """Check if a numeric value is within optional [min, max] bounds."""
    if min_value is not None and value < min_value:
        return False
    if max_value is not None and value > max_value:
        return False
    return True


def _bool_match(user_value: bool, req_value: bool | None) -> bool:
    """Three-state boolean match: None means 'no constraint'."""
    if req_value is None:
        return True
    return user_value == req_value


# Removed flat requirements matching


def _node_matches_business(business: BusinessInput, node: SectionNode) -> bool:
    """Apply structured constraints on a single node against the business profile."""
    if not _within_range(business.area_sqm, node.min_area_sqm, node.max_area_sqm):
        return False
    if not _within_range(business.seats, node.min_seats, node.max_seats):
        return False
    if not _bool_match(business.uses_gas, node.requires_gas):
        return False
    if not _bool_match(business.serves_meat, node.serves_meat):
        return False
    if not _bool_match(business.offers_delivery, node.offers_delivery):
        return False
    return True


def match_structure(business: BusinessInput, tree: List[SectionNode]) -> List[SectionNode]:
    """Basic matching: keep nodes that match or have matched descendants."""
    results: List[SectionNode] = []

    def dfs(node: SectionNode) -> SectionNode | None:
        matched_children: List[SectionNode] = []
        for child in node.children:
            sub = dfs(child)
            if sub is not None:
                matched_children.append(sub)
        if _node_matches_business(business, node) or matched_children:
            return SectionNode(
                id=node.id,
                level=node.level,
                title=node.title,
                text=node.text,
                context=node.context,
                group_level=node.group_level,
                min_area_sqm=node.min_area_sqm,
                max_area_sqm=node.max_area_sqm,
                min_seats=node.min_seats,
                max_seats=node.max_seats,
                requires_gas=node.requires_gas,
                serves_meat=node.serves_meat,
                offers_delivery=node.offers_delivery,
                children=matched_children,
            )
        return None

    for root in tree:
        m = dfs(root)
        if m is not None:
            results.append(m)
    return results


def _contains_any_word(text: str, words: List[str]) -> bool:
    """Whole-word containment test using Unicode-aware boundaries."""
    # Whole-word match using Unicode-aware boundaries
    for w in words:
        if re.search(rf"(?<!\w){re.escape(w)}(?!\w)", text, flags=re.UNICODE):
            return True
    return False


def _extract_ints(text: str) -> List[int]:
    """Extract up to 4-digit integers from text (used for area/seat hints)."""
    vals: List[int] = []
    for m in re.finditer(r"\b(\d{1,4})\b", text):
        try:
            vals.append(int(m.group(1)))
        except Exception:
            pass
    return vals


def _area_matches(text: str, area_sqm: float) -> bool:
    """Heuristic area matcher: looks for explicit comparisons relative to area."""
    t = text
    # Must contain an area term as a whole word
    area_terms = ["שטח", "שטחים", "מ\"ר", "מ'", "מ׳"]
    if not _contains_any_word(t, area_terms):
        return False
    # exact number present anywhere
    if int(area_sqm) in _extract_ints(t):
        return True

    # Comparison-based matching: parse explicit relations
    # Allow separator after מ/ל like hyphen or Hebrew maqaf/quotes
    # Allow separators after prepositions like מ/ל: hyphen, en/em dash, Hebrew geresh/gershayim, maqaf
    # Use single-quoted raw string to avoid escaping issues and SyntaxWarning
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

    def any_match(patterns, predicate) -> bool:
        for p in patterns:
            m = re.search(p, t, flags=re.UNICODE)
            if m:
                try:
                    n = int(m.group(1))
                    if predicate(n):
                        return True
                except Exception:
                    continue
        return False

    if any_match(gt_patterns, lambda n: area_sqm > n):
        return True
    if any_match(lt_patterns, lambda n: area_sqm < n):
        return True
    if any_match(ge_patterns, lambda n: area_sqm >= n):
        return True
    if any_match(le_patterns, lambda n: area_sqm <= n):
        return True

    return False


def _advanced_node_match(business: BusinessInput, node: SectionNode) -> bool:
    """Advanced matcher combining structured fields with keyword heuristics."""
    text = node.text or ""
    # 2) seats rule: if < 200 never show 3.2.1
    if business.seats < 200 and node.id == "3.2.1":
        return False
    # Structured pre-filters if present on node
    if node.min_area_sqm is not None and business.area_sqm < node.min_area_sqm:
        return False
    if node.max_area_sqm is not None and business.area_sqm > node.max_area_sqm:
        return False
    if node.min_seats is not None and business.seats < node.min_seats:
        return False
    if node.max_seats is not None and business.seats > node.max_seats:
        return False
    if node.requires_gas is not None and business.uses_gas != node.requires_gas:
        return False
    if node.serves_meat is not None and business.serves_meat != node.serves_meat:
        return False
    if node.offers_delivery is not None and business.offers_delivery != node.offers_delivery:
        return False

    matched = False
    # 1) area
    if business.area_sqm is not None:
        matched = matched or _area_matches(text, business.area_sqm)
    # 3) gas
    if business.uses_gas:
        gas_patterns = [
            r"(?<!\w)ה?גז(?:ים)?(?!\w)",                      # גז / הגז / גזים / הגזים
            r"(?<!\w)ה?גפ['\"׳]?[[מם]](?!\w)",              # גפ"מ / הגפ"מ with מ or ם
            r"(?<!\w)ה?גפ['\"׳]?\u05DD(?!\w)",            # final mem ם explicit fallback
            r"(?<!\w)ה?גפ['\"׳]?\u05DE(?!\w)",            # regular mem מ explicit fallback
        ]
        matched = matched or any(re.search(p, text, flags=re.UNICODE) for p in gas_patterns)
    # 4) meat
    if business.serves_meat:
        matched = matched or bool(re.search(r"(?<!\w)בשר(?!\w)", text, flags=re.UNICODE))
    # 5) delivery
    if business.offers_delivery:
        matched = matched or bool(re.search(r"(?<!\w)משלוח(?:ים)?(?!\w)", text, flags=re.UNICODE))
    return matched


def match_structure_advanced(business: BusinessInput, tree: List[SectionNode]) -> List[SectionNode]:
    """Build a pruned tree of relevant nodes.

    If a node matches, include the entire subtree for context; otherwise include
    only the matched descendants.
    """
    results: List[SectionNode] = []

    # Build a flat index of all nodes to support subtree reconstruction even if
    # descendants were not nested correctly during parsing
    flat: Dict[str, SectionNode] = {}

    def index_nodes(nodes: List[SectionNode]):
        for n in nodes:
            flat[n.id] = n
            if n.children:
                index_nodes(n.children)

    index_nodes(tree)

    def build_subtree(prefix: str, context: str | None) -> SectionNode | None:
        root = flat.get(prefix)
        if root is None:
            return None
        # Collect all descendant ids that begin with prefix + '.' and same context
        descendants = [n for nid, n in flat.items() if n.context == context and (nid == prefix or nid.startswith(prefix + "."))]
        # Create shallow copies and map by id
        copies: Dict[str, SectionNode] = {}
        for n in descendants:
            copies[n.id] = SectionNode(
                id=n.id,
                level=n.level,
                text=n.text,
                context=n.context,
                group_level=n.group_level,
                min_area_sqm=n.min_area_sqm,
                max_area_sqm=n.max_area_sqm,
                min_seats=n.min_seats,
                max_seats=n.max_seats,
                requires_gas=n.requires_gas,
                serves_meat=n.serves_meat,
                offers_delivery=n.offers_delivery,
                children=[],
            )
        # Link copies by parent id
        for nid, cn in list(copies.items()):
            if nid == prefix:
                continue
            parent_id = nid.rsplit('.', 1)[0]
            parent = copies.get(parent_id)
            if parent is not None:
                parent.children.append(cn)
        return copies.get(prefix)

    def dfs(node: SectionNode) -> SectionNode | None:
        matched_children: List[SectionNode] = []
        for child in node.children:
            sub = dfs(child)
            if sub is not None:
                matched_children.append(sub)
        # If this node matches, include it and all lower-level descendants in same context
        if _advanced_node_match(business, node):
            return build_subtree(node.id, node.context)
        # Otherwise, include only matched subtree
        if matched_children:
            return SectionNode(
                id=node.id,
                level=node.level,
                text=node.text,
                context=node.context,
                group_level=node.group_level,
                min_area_sqm=node.min_area_sqm,
                max_area_sqm=node.max_area_sqm,
                min_seats=node.min_seats,
                max_seats=node.max_seats,
                requires_gas=node.requires_gas,
                serves_meat=node.serves_meat,
                offers_delivery=node.offers_delivery,
                children=matched_children,
            )
        return None

    for root in tree:
        m = dfs(root)
        if m is not None:
            results.append(m)
    return results



