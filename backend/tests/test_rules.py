from __future__ import annotations

import pytest

from app.rules import allocate_filename, extract_candidates, safe_stem


def test_certify_anchor_extracts_company_name() -> None:
    text = (
        "CERTIFICATE OF INCORPORATION\n"
        "This is to certify that\n"
        "NORTHSTAR LOGISTICS CORPORATION\n"
        "has been duly incorporated under existing laws."
    )
    assert extract_candidates(text) == ["NORTHSTAR LOGISTICS CORPORATION"]


def test_secretary_certificate_ignores_bank_in_resolution() -> None:
    text = (
        "SECRETARY'S CERTIFICATE\n"
        "I, Jane Doe, Corporate Secretary of HARBORLINE FOODS, INC. (the 'Corporation'),\n"
        "do hereby certify that the Board resolved to open an account with METRO TRUST BANK CORP."
    )
    assert extract_candidates(text) == ["HARBORLINE FOODS, INC."]


def test_gis_corporate_name_field() -> None:
    text = (
        "GENERAL INFORMATION SHEET (GIS)\n"
        "1. CORPORATE NAME: PACIFIC RIDGE SOLAR HOLDINGS, CORP.\n"
        "2. DATE REGISTERED: 2024-05-10"
    )
    assert extract_candidates(text) == ["PACIFIC RIDGE SOLAR HOLDINGS, CORP."]


def test_articles_first_clause() -> None:
    text = (
        "ARTICLES OF INCORPORATION\n"
        "FIRST: That the name of the corporation shall be:\n"
        "VERDANT AGRI VENTURES INCORPORATED\n"
        "SECOND: That the primary purpose..."
    )
    assert extract_candidates(text) == ["VERDANT AGRI VENTURES INCORPORATED"]


def test_page_boundary_prevents_cross_page_authorization() -> None:
    text = (
        "CERTIFICATE OF INCORPORATION\n\f"
        "KNOW ALL PERSONS BY THESE PRESENTS:\n"
        "ORION BUILDERS CORP.\n"
    )
    assert extract_candidates(text) == []


def test_safe_stem_sanitizes_and_prefixes_windows_reserved() -> None:
    assert safe_stem('Acme / Global: "Logistics" Inc.') == "Acme Global Logistics Inc"
    assert safe_stem("CON") == "_CON"
    with pytest.raises(ValueError):
        safe_stem("   ")


def test_allocate_filename_handles_collisions_case_insensitively() -> None:
    existing = ["Northstar Logistics Corp.pdf", "northstar logistics corp (1).pdf"]
    assert (
        allocate_filename("Northstar Logistics Corp", ".pdf", existing)
        == "Northstar Logistics Corp (2).pdf"
    )
