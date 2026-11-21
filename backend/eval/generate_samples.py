from __future__ import annotations

from pathlib import Path

import pymupdf
from openpyxl import Workbook

SAMPLES_DIR = Path(__file__).resolve().parents[2] / "sample-docs"

DOCS = {
    "scan_001.pdf": (
        "REPUBLIC OF EXAMPLE\n"
        "CORPORATE REGISTRY COMMISSION\n\n"
        "CERTIFICATE OF INCORPORATION\n\n"
        "This is to certify that\n"
        "NORTHSTAR LOGISTICS CORPORATION\n"
        "has been duly incorporated under existing laws.\n\n"
        "Issued on March 14, 2025. Fictional sample document."
    ),
    "scan_002.pdf": (
        "SECRETARY'S CERTIFICATE\n\n"
        "I, Maria Santos, Corporate Secretary of HARBORLINE FOODS, INC. (the 'Corporation'),\n"
        "do hereby certify that at a regular meeting of the Board of Directors,\n"
        "the Board resolved to authorize account opening with METRO TRUST BANK CORP.\n\n"
        "Fictional sample document."
    ),
    "scan_003.pdf": (
        "GENERAL INFORMATION SHEET (GIS)\n\n"
        "1. CORPORATE NAME: PACIFIC RIDGE SOLAR HOLDINGS, CORP.\n"
        "2. DATE REGISTERED: May 10, 2024\n"
        "3. PRINCIPAL OFFICE: 120 Sample Ave., Metro City\n\n"
        "Fictional sample document."
    ),
}

COMPANIES = [
    "Northstar Logistics Corp.",
    "Harborline Foods, Inc.",
    "Pacific Ridge Solar Holdings, Corp.",
    "Verdant Agri Ventures Incorporated",
]


def main() -> None:
    SAMPLES_DIR.mkdir(parents=True, exist_ok=True)
    for filename, text in DOCS.items():
        doc = pymupdf.open()
        page = doc.new_page()
        page.insert_text((72, 72), text, fontsize=12)
        doc.save(SAMPLES_DIR / filename)
        doc.close()

    wb = Workbook()
    ws = wb.active
    assert ws is not None
    ws.title = "Companies"
    ws.append(["Company Name"])
    for company in COMPANIES:
        ws.append([company])
    wb.save(SAMPLES_DIR / "company-registry.xlsx")
    print(f"Generated {len(DOCS)} sample PDFs and company-registry.xlsx in {SAMPLES_DIR}")


if __name__ == "__main__":
    main()
