from __future__ import annotations

import pytest

from app.config import Settings
from app.ocr import OCRResult
from app.pipeline import analyze_document_bytes
from app.schemas import LLMExtractionResult


@pytest.mark.asyncio
async def test_pipeline_uses_deterministic_rules_without_calling_llm(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    called = False

    async def fake_llm(*args, **kwargs):
        nonlocal called
        called = True

    monkeypatch.setattr("app.pipeline.extract_with_llm_fallback", fake_llm)

    ocr = OCRResult(
        text="This is to certify that NORTHSTAR LOGISTICS CORP. has been registered.",
        page_count=1,
        source="pdf_text",
    )
    cfg = Settings(llm_provider="gemini", gemini_api_key="test-key")
    res = await analyze_document_bytes(
        filename="scan001.pdf",
        content=b"%PDF-1.4 fake",
        companies=["Northstar Logistics Corp."],
        use_llm_fallback=True,
        cfg=cfg,
        ocr_override=ocr,
    )
    assert called is False
    assert res.method == "company_list_exact"
    assert res.suggested_name == "Northstar Logistics Corp."
    assert res.safe_filename == "Northstar Logistics Corp.pdf"
    assert res.confidence == 0.98


@pytest.mark.asyncio
async def test_pipeline_invokes_llm_fallback_when_rules_abstain(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def fake_llm(ocr_text: str, companies: list[str], cfg: Settings):
        return LLMExtractionResult(
            company_name="Summit Cloud Systems Inc.",
            confidence=0.88,
            evidence_quote="Issued to Summit Cloud Systems Inc.",
            reasoning="Identified primary entity from non-standard registration layout.",
        )

    monkeypatch.setattr("app.pipeline.extract_with_llm_fallback", fake_llm)

    ocr = OCRResult(
        text="NON-STANDARD REGISTRATION NOTICE\nIssued to Summit Cloud Systems Inc.",
        page_count=1,
        source="rapidocr",
    )
    cfg = Settings(llm_provider="gemini", gemini_api_key="test-key")
    res = await analyze_document_bytes(
        filename="photo.png",
        content=b"fake-png-bytes",
        companies=[],
        use_llm_fallback=True,
        cfg=cfg,
        ocr_override=ocr,
    )
    assert res.llm_used is True
    assert res.method == "llm_fallback"
    assert res.suggested_name == "Summit Cloud Systems Inc."
    assert res.safe_filename == "Summit Cloud Systems Inc.png"
    assert res.confidence == 0.88
