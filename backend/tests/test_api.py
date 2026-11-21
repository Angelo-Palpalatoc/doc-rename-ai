from __future__ import annotations

import io
import json
import zipfile

import pymupdf
from fastapi.testclient import TestClient
from PIL import Image

from app.main import app

client = TestClient(app)


def _make_pdf(text: str) -> bytes:
    doc = pymupdf.open()
    page = doc.new_page()
    page.insert_text((72, 72), text, fontsize=12)
    data = doc.tobytes()
    doc.close()
    return data


def test_health_endpoint() -> None:
    res = client.get("/api/health")
    assert res.status_code == 200
    body = res.json()
    assert body["status"] == "ok"
    assert "RapidOCR" in body["ocr_engine"]


def test_analyze_pdf_and_export_zip_preserves_original_bytes() -> None:
    pdf_bytes = _make_pdf(
        "CERTIFICATE OF INCORPORATION\n\n"
        "This is to certify that\n"
        "PACIFIC RIDGE SOLAR HOLDINGS CORP.\n"
        "has been duly incorporated."
    )
    analyze_res = client.post(
        "/api/analyze",
        files={"file": ("raw_scan.pdf", pdf_bytes, "application/pdf")},
        data={"companies_json": json.dumps(["Pacific Ridge Solar Holdings Corp."])},
    )
    assert analyze_res.status_code == 200
    payload = analyze_res.json()
    assert payload["suggested_name"] == "Pacific Ridge Solar Holdings Corp."
    assert payload["method"] == "company_list_exact"
    assert payload["ocr_source"] == "pdf_text"

    export_res = client.post(
        "/api/export-zip",
        files=[
            ("files", ("raw_scan.pdf", pdf_bytes, "application/pdf")),
            ("files", ("raw_scan_dup.pdf", pdf_bytes, "application/pdf")),
        ],
        data={
            "target_names_json": json.dumps(
                ["Pacific Ridge Solar Holdings Corp.", "Pacific Ridge Solar Holdings Corp."]
            )
        },
    )
    assert export_res.status_code == 200
    with zipfile.ZipFile(io.BytesIO(export_res.content)) as zf:
        names = sorted(zf.namelist())
        assert names == [
            "Pacific Ridge Solar Holdings Corp (1).pdf",
            "Pacific Ridge Solar Holdings Corp.pdf",
        ]
        assert zf.read(names[0]) == pdf_bytes
        assert zf.read(names[1]) == pdf_bytes


def test_company_list_csv_upload() -> None:
    csv_bytes = b'No.,Company Name\n1,Northstar Logistics Corp.\n2,"Harborline Foods, Inc."\n'
    res = client.post(
        "/api/company-list",
        files={"file": ("registry.csv", csv_bytes, "text/csv")},
    )
    assert res.status_code == 200
    body = res.json()
    assert body["count"] == 2
    assert body["companies"] == ["Northstar Logistics Corp.", "Harborline Foods, Inc."]


def test_analyze_png_exercises_rapidocr_runtime() -> None:
    buf = io.BytesIO()
    Image.new("RGB", (320, 120), color="white").save(buf, format="PNG")
    res = client.post(
        "/api/analyze",
        files={"file": ("blank_scan.png", buf.getvalue(), "image/png")},
    )
    assert res.status_code == 200
    payload = res.json()
    assert payload["ocr_source"] == "rapidocr"
    assert payload["method"] == "needs_review"
