from __future__ import annotations

from app.matcher import resolve_company_match


def test_exact_company_list_match_ignores_punctuation() -> None:
    text = "This is to certify that HARBORLINE FOODS INC has been registered."
    companies = ["Harborline Foods, Inc.", "Northstar Logistics Corp."]
    result = resolve_company_match(text, companies)
    assert result.suggested_name == "Harborline Foods, Inc."
    assert result.matched_from_list is True
    assert result.match_kind == "exact"
    assert result.ambiguous is False


def test_fuzzy_company_list_match_tolerates_single_ocr_typo() -> None:
    text = "This is to certify that NORTHSTAK LOGISTICS CORPORATION has been registered."
    companies = ["Northstar Logistics Corp."]
    result = resolve_company_match(text, companies)
    assert result.suggested_name == "Northstar Logistics Corp."
    assert result.matched_from_list is True
    assert result.match_kind == "fuzzy"


def test_fuzzy_match_rejects_different_legal_entity_types() -> None:
    text = "This is to certify that NORTHSTAR LOGISTICS INCORPORATED has been registered."
    companies = ["Northstar Logistics Corp."]
    result = resolve_company_match(text, companies)
    assert result.matched_from_list is False
    assert result.match_kind == "rules_only"
    assert result.suggested_name == "NORTHSTAR LOGISTICS INCORPORATED"


def test_multiple_distinct_candidates_flagged_ambiguous() -> None:
    text = (
        "This is to certify that ALPHA TRADING CORP. has been registered.\n"
        "This is to certify that BETA TRADING CORP. has been registered."
    )
    result = resolve_company_match(text, [])
    assert result.ambiguous is True
    assert result.suggested_name is None
