from __future__ import annotations

import re

from app.rules import extract_candidates
from app.schemas import CompanyMatchResult

PUNCTUATION = re.compile(r"[.,'’]")
WHITESPACE = re.compile(r"\s+")

LEGAL_FORMS: dict[str, str] = {
    "INC": "INC",
    "INCORPORATED": "INC",
    "CORP": "CORP",
    "CORPORATION": "CORP",
    "CO": "CO",
    "COMPANY": "CO",
    "LTD": "LTD",
    "LIMITED": "LTD",
    "OPC": "OPC",
    "PARTNERSHIP": "PARTNERSHIP",
    "LLC": "LLC",
    "LLP": "LLP",
}


def normalize_company_name(value: str) -> str:
    """Ignore presentation punctuation while preserving word boundaries and entity type."""
    cleaned = PUNCTUATION.sub("", value.upper())
    return WHITESPACE.sub(" ", cleaned).strip()


def resolve_company_match(text: str, companies: list[str]) -> CompanyMatchResult:
    """Resolve extracted document candidates against an optional company registry."""
    raw_candidates = extract_candidates(text)
    seen_keys: set[str] = set()
    candidates: list[str] = []
    for candidate in raw_candidates:
        key = normalize_company_name(candidate)
        if key not in seen_keys:
            seen_keys.add(key)
            candidates.append(candidate)

    if not candidates:
        return CompanyMatchResult()
    if len(candidates) != 1:
        return CompanyMatchResult(ambiguous=True)

    evidence = candidates[0]
    key = normalize_company_name(evidence)

    unique_entries: list[str] = []
    seen_entries: set[str] = set()
    for entry in companies:
        stripped = entry.strip()
        if not stripped:
            continue
        entry_key = normalize_company_name(stripped)
        if entry_key not in seen_entries:
            seen_entries.add(entry_key)
            unique_entries.append(stripped)

    for entry in unique_entries:
        if normalize_company_name(entry) == key:
            return CompanyMatchResult(
                suggested_name=entry,
                evidence=evidence,
                matched_from_list=True,
                match_kind="exact",
            )

    near = [entry for entry in unique_entries if _is_nearby(key, normalize_company_name(entry))]
    if len(near) == 0:
        return CompanyMatchResult(
            suggested_name=evidence,
            evidence=evidence,
            matched_from_list=False,
            match_kind="rules_only",
        )
    if len(near) == 1:
        return CompanyMatchResult(
            suggested_name=near[0],
            evidence=evidence,
            matched_from_list=True,
            match_kind="fuzzy",
        )
    return CompanyMatchResult(evidence=evidence, ambiguous=True, match_kind="none")


def _is_nearby(left: str, right: str) -> bool:
    """Strict fuzzy match for OCR typos without conflating distinct legal forms or short tokens."""
    a = left.split(" ")
    b = right.split(" ")
    if len(a) != len(b) or len(a) < 2:
        return False

    form_a = LEGAL_FORMS.get(a[-1])
    form_b = LEGAL_FORMS.get(b[-1])
    if form_a is not None and form_b is not None and form_a != form_b:
        return False

    body_a = " ".join(a[:-1])
    body_b = " ".join(b[:-1])
    if min(len(body_a), len(body_b)) < 8:
        return False

    for token_a, token_b in zip(a[:-1], b[:-1], strict=True):
        if token_a != token_b and (
            min(len(token_a), len(token_b)) < 5
            or any(ch.isdigit() for ch in token_a)
            or any(ch.isdigit() for ch in token_b)
        ):
            return False

    limit = 2 if min(len(body_a), len(body_b)) >= 15 else 1
    suffix_cost = (
        0 if (form_a is not None and form_a == form_b) else _osa_distance(a[-1], b[-1], limit)
    )
    if suffix_cost > limit:
        return False
    return _osa_distance(body_a, body_b, limit - suffix_cost) + suffix_cost <= limit


def _osa_distance(a: str, b: str, limit: int) -> int:
    """Bounded Optimal String Alignment distance (includes adjacent transpositions)."""
    if a == b:
        return 0
    if abs(len(a) - len(b)) > limit:
        return limit + 1

    before_prev = [0] * (len(b) + 1)
    prev = list(range(len(b) + 1))

    for i in range(1, len(a) + 1):
        curr = [0] * (len(b) + 1)
        curr[0] = i
        row_min = i
        for j in range(1, len(b) + 1):
            cost = 0 if a[i - 1] == b[j - 1] else 1
            best = min(curr[j - 1] + 1, prev[j] + 1, prev[j - 1] + cost)
            if i > 1 and j > 1 and a[i - 1] == b[j - 2] and a[i - 2] == b[j - 1]:
                best = min(best, before_prev[j - 2] + 1)
            curr[j] = best
            row_min = min(row_min, best)
        if row_min > limit:
            return limit + 1
        before_prev = prev
        prev = curr

    return prev[len(b)]
