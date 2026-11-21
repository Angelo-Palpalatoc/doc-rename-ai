from __future__ import annotations

import asyncio
import hashlib
import time
from pathlib import Path

from app.config import Settings, settings
from app.llm import extract_with_llm_fallback
from app.matcher import resolve_company_match
from app.ocr import OCRResult, extract_document_text
from app.rules import safe_stem
from app.schemas import AnalyzeDocumentResponse, ExtractionMethod

SUPPORTED_EXTENSIONS = {".pdf", ".png", ".jpg", ".jpeg"}


async def analyze_document_bytes(
    filename: str,
    content: bytes,
    companies: list[str] | None = None,
    use_llm_fallback: bool = True,
    cfg: Settings | None = None,
    ocr_override: OCRResult | None = None,
) -> AnalyzeDocumentResponse:
    """Run the full hybrid extraction pipeline on document bytes."""
    started = time.perf_counter()
    active_cfg = cfg or settings
    company_list = companies or []

    ext = Path(filename).suffix.lower()
    if ext not in SUPPORTED_EXTENSIONS:
        raise ValueError(f"Unsupported file type '{ext}'. Allowed: PDF, PNG, JPG.")

    sha256 = hashlib.sha256(content).hexdigest()
    ocr_result = ocr_override or await asyncio.to_thread(extract_document_text, content, ext)
    match = resolve_company_match(ocr_result.text, company_list)

    suggested_name = match.suggested_name
    evidence = match.evidence
    ambiguous = match.ambiguous
    llm_used = False
    llm_reasoning: str | None = None

    method: ExtractionMethod
    confidence: float

    if match.match_kind == "exact":
        method = "company_list_exact"
        confidence = 0.98
    elif match.match_kind == "fuzzy":
        method = "company_list_fuzzy"
        confidence = 0.90
    elif match.match_kind == "rules_only":
        method = "deterministic_rules"
        confidence = 0.85
    else:
        method = "needs_review"
        confidence = 0.0

    # Stage 2: Optional structured-output LLM fallback when deterministic rules abstain or are ambiguous
    if use_llm_fallback and method == "needs_review" and active_cfg.llm_configured:
        llm_result = await extract_with_llm_fallback(ocr_result.text, company_list, active_cfg)
        if llm_result is not None:
            llm_used = True
            llm_reasoning = llm_result.reasoning or None
            if llm_result.company_name and llm_result.confidence >= 0.55:
                suggested_name = llm_result.company_name.strip()
                evidence = llm_result.evidence_quote or evidence
                confidence = round(llm_result.confidence, 2)
                method = "llm_fallback"
                ambiguous = False

    safe_filename: str | None = None
    if suggested_name:
        try:
            safe_filename = f"{safe_stem(suggested_name)}{ext}"
        except ValueError:
            safe_filename = None

    excerpt = " ".join(ocr_result.text.split())[:360]
    latency_ms = int((time.perf_counter() - started) * 1000)

    return AnalyzeDocumentResponse(
        original_filename=filename,
        extension=ext,
        sha256=sha256,
        size_bytes=len(content),
        page_count=ocr_result.page_count,
        ocr_source=ocr_result.source,
        suggested_name=suggested_name,
        safe_filename=safe_filename,
        confidence=confidence,
        method=method,
        ambiguous=ambiguous,
        evidence=evidence,
        ocr_excerpt=excerpt,
        llm_used=llm_used,
        llm_reasoning=llm_reasoning,
        latency_ms=latency_ms,
    )
