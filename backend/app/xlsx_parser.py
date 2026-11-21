from __future__ import annotations

import csv
import io
from pathlib import Path

from openpyxl import load_workbook

from app.matcher import normalize_company_name

COMPANY_HEADER_ALIASES = {
    "company name",
    "company names",
    "corporate name",
    "registered company name",
    "company",
    "entity",
    "client",
    "name",
}


def parse_company_list(filename: str, content: bytes) -> list[str]:
    """Parse company names from an uploaded .xlsx or .csv file.

    Detects the company-name header column (matching Android CompanyListReader)
    instead of blindly reading Column A, which is often a row index or ID.
    """
    ext = Path(filename).suffix.lower()
    if ext == ".xlsx":
        rows = _read_xlsx_rows(content)
    elif ext == ".csv":
        rows = _read_csv_rows(content)
    else:
        raise ValueError("Company list must be an .xlsx or .csv file.")

    raw_values = _extract_company_column(rows)

    seen: set[str] = set()
    cleaned: list[str] = []
    for raw in raw_values:
        value = " ".join(raw.split()).strip()
        if not value or value.lower() in COMPANY_HEADER_ALIASES:
            continue
        if not any(ch.isalpha() for ch in value):
            continue
        key = normalize_company_name(value)
        if key and key not in seen:
            seen.add(key)
            cleaned.append(value)
    return cleaned


def _extract_company_column(rows: list[list[str]]) -> list[str]:
    if not rows:
        return []

    # 1. Search first 20 rows for a known company-name header column.
    for row_idx, row in enumerate(rows[:20]):
        for col_idx, cell in enumerate(row):
            normalized = " ".join(cell.lower().split()).strip()
            if normalized in COMPANY_HEADER_ALIASES:
                return [
                    r[col_idx]
                    for r in rows[row_idx + 1 :]
                    if col_idx < len(r) and r[col_idx].strip()
                ]

    # 2. Fallback: choose the column with the most alphabetic text entries (skipping numeric IDs).
    max_cols = max((len(r) for r in rows), default=0)
    best_col = 0
    best_score = -1
    for col_idx in range(max_cols):
        score = sum(
            1
            for r in rows[:200]
            if col_idx < len(r)
            and any(ch.isalpha() for ch in r[col_idx])
            and len(r[col_idx].strip()) >= 4
        )
        if score > best_score:
            best_score = score
            best_col = col_idx

    return [r[best_col] for r in rows if best_col < len(r) and r[best_col].strip()]


def _read_xlsx_rows(content: bytes) -> list[list[str]]:
    wb = load_workbook(io.BytesIO(content), read_only=True, data_only=True)
    try:
        sheet = wb.active
        if sheet is None:
            return []
        rows: list[list[str]] = []
        for row in sheet.iter_rows(values_only=True):
            rows.append(["" if cell is None else str(cell).strip() for cell in row])
        return rows
    finally:
        wb.close()


def _read_csv_rows(content: bytes) -> list[list[str]]:
    decoded = content.decode("utf-8-sig", errors="replace")
    reader = csv.reader(io.StringIO(decoded))
    return [[cell.strip() for cell in row] for row in reader]
