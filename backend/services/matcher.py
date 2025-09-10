from typing import List

from ..models import BusinessInput, Requirement, SectionNode


def _within_range(value, min_value, max_value) -> bool:
    if min_value is not None and value < min_value:
        return False
    if max_value is not None and value > max_value:
        return False
    return True


def _bool_match(user_value: bool, req_value: bool | None) -> bool:
    if req_value is None:
        return True
    return user_value == req_value


def match_requirements(business: BusinessInput, requirements: List[Requirement]) -> List[Requirement]:
    matched: List[Requirement] = []
    for req in requirements:
        if not _within_range(business.area_sqm, req.min_area_sqm, req.max_area_sqm):
            continue
        if not _within_range(business.seats, req.min_seats, req.max_seats):
            continue
        if not _bool_match(business.uses_gas, req.requires_gas):
            continue
        if not _bool_match(business.serves_meat, req.serves_meat):
            continue
        if not _bool_match(business.offers_delivery, req.offers_delivery):
            continue
        matched.append(req)
    return matched


def _node_matches_business(business: BusinessInput, node: SectionNode) -> bool:
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



