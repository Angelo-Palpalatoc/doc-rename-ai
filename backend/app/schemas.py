from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

ExtractionMethod = Literal[
    "company_list_exact",
    "company_list_fuzzy",
    "deterministic_rules",
    "llm_fallback",
    "needs_review",
]


class HealthResponse(BaseModel):
    status: Literal["ok"] = "ok"
    ocr_engine: str
    llm_provider: str
    llm_configured: bool


class CompanyMatchResult(BaseModel):
    suggested_name: str | None = None
    evidence: str | None = None
    ambiguous: bool = False
    matched_from_list: bool = False
    match_kind: Literal["exact", "fuzzy", "rules_only", "none"] = "none"


class LLMExtractionResult(BaseModel):
    """Strict structured output contract returned by the optional LLM fallback."""

    company_name: str | None = Field(
        default=None,
        description="Official legal name of the primary document holder, or null if uncertain.",
    )
    confidence: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Model self-assessed confidence in [0.0, 1.0].",
    )
    evidence_quote: str | None = Field(
        default=None,
        description="Short verbatim snippet from the document supporting the extracted name.",
    )
    reasoning: str = Field(
        default="",
        description="One-sentence justification for the extraction or abstention.",
    )


class AnalyzeDocumentResponse(BaseModel):
    original_filename: str
    extension: str
    sha256: str
    size_bytes: int
    page_count: int
    ocr_source: Literal["pdf_text", "rapidocr", "hybrid"]
    suggested_name: str | None
    safe_filename: str | None
    confidence: float = Field(ge=0.0, le=1.0)
    method: ExtractionMethod
    ambiguous: bool = False
    evidence: str | None = None
    ocr_excerpt: str = ""
    llm_used: bool = False
    llm_reasoning: str | None = None
    latency_ms: int


class CompanyListResponse(BaseModel):
    count: int
    companies: list[str]
    source_filename: str
