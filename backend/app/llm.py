from __future__ import annotations

import json
import logging

import httpx

from app.config import Settings
from app.schemas import LLMExtractionResult

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You extract the official legal company name of the PRIMARY document holder from corporate documents (certificates of incorporation, articles, general information sheets, secretary's certificates, registrations, or invoices).

Rules:
1. Return ONLY valid JSON matching the schema:
   {"company_name": string | null, "confidence": number (0.0-1.0), "evidence_quote": string | null, "reasoning": string}
2. Prefer an exact entry from the provided company registry if the document clearly belongs to it.
3. Ignore banks, notaries, witnesses, and government agencies (e.g. SEC, BIR, DTI) unless they are the actual subject company.
4. If the document is ambiguous or does not clearly identify a single primary company, set company_name to null and confidence <= 0.3.
"""


def _build_user_prompt(ocr_text: str, companies: list[str]) -> str:
    trimmed_text = ocr_text[:6000]
    registry_block = ""
    if companies:
        sample = "\n".join(f"- {name}" for name in companies[:100])
        registry_block = f"\nKnown company registry (prefer exact spelling if matched):\n{sample}\n"
    return f"{registry_block}\nDocument OCR text:\n---\n{trimmed_text}\n---"


def _parse_json_payload(raw_text: str) -> LLMExtractionResult:
    cleaned = raw_text.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.strip("`")
        if cleaned.lower().startswith("json"):
            cleaned = cleaned[4:].strip()
    data = json.loads(cleaned)
    return LLMExtractionResult.model_validate(data)


async def extract_with_llm_fallback(
    ocr_text: str,
    companies: list[str],
    cfg: Settings,
) -> LLMExtractionResult | None:
    """Call the configured LLM provider with strict Pydantic output validation.

    Returns None if no provider is configured or if the upstream call fails.
    """
    if not cfg.llm_configured or not ocr_text.strip():
        return None

    user_prompt = _build_user_prompt(ocr_text, companies)

    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            if cfg.llm_provider == "gemini":
                return await _call_gemini(client, user_prompt, cfg)
            if cfg.llm_provider == "openai":
                return await _call_openai(client, user_prompt, cfg)
            if cfg.llm_provider == "ollama":
                return await _call_ollama(client, user_prompt, cfg)
    except Exception as exc:  # noqa: BLE001
        logger.warning("LLM fallback (%s) failed: %s", cfg.llm_provider, exc)
        return None

    return None


async def _call_gemini(
    client: httpx.AsyncClient,
    user_prompt: str,
    cfg: Settings,
) -> LLMExtractionResult:
    url = (
        f"https://generativelanguage.googleapis.com/v1beta/models/"
        f"{cfg.gemini_model}:generateContent"
    )
    payload = {
        "system_instruction": {"parts": [{"text": SYSTEM_PROMPT}]},
        "contents": [{"parts": [{"text": user_prompt}]}],
        "generationConfig": {
            "temperature": 0.0,
            "responseMimeType": "application/json",
        },
    }
    resp = await client.post(url, params={"key": cfg.gemini_api_key}, json=payload)
    resp.raise_for_status()
    body = resp.json()
    text = body["candidates"][0]["content"]["parts"][0]["text"]
    return _parse_json_payload(text)


async def _call_openai(
    client: httpx.AsyncClient,
    user_prompt: str,
    cfg: Settings,
) -> LLMExtractionResult:
    payload = {
        "model": cfg.openai_model,
        "temperature": 0.0,
        "response_format": {"type": "json_object"},
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
    }
    resp = await client.post(
        "https://api.openai.com/v1/chat/completions",
        headers={"Authorization": f"Bearer {cfg.openai_api_key}"},
        json=payload,
    )
    resp.raise_for_status()
    text = resp.json()["choices"][0]["message"]["content"]
    return _parse_json_payload(text)


async def _call_ollama(
    client: httpx.AsyncClient,
    user_prompt: str,
    cfg: Settings,
) -> LLMExtractionResult:
    payload = {
        "model": cfg.ollama_model,
        "stream": False,
        "format": "json",
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
    }
    resp = await client.post(f"{cfg.ollama_base_url.rstrip('/')}/api/chat", json=payload)
    resp.raise_for_status()
    text = resp.json()["message"]["content"]
    return _parse_json_payload(text)
