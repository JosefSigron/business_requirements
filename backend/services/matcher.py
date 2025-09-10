from typing import List

from ..models import BusinessInput, Requirement


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



