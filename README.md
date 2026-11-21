# DocRename AI

Hybrid **Next.js (TypeScript) + FastAPI (Python)** document OCR and intelligent auto-renaming workspace.

Built as an AI Engineering portfolio project demonstrating a **deterministic-first, LLM-fallback extraction pipeline**:

1. **Content Hashing (`SHA-256`)** — Detects exact duplicate uploads before running OCR or exporting.
2. **Local Document Extraction (`PyMuPDF` + `RapidOCR`)** — Extracts embedded PDF text instantly and runs local ONNX OCR on scanned PDFs, PNGs, and JPGs with zero external system binaries.
3. **Deterministic Rules & Company-List Matching** — Applies page-isolated corporate clause rules and bounded Optimal String Alignment (OSA) fuzzy matching against an optional uploaded `.xlsx` / `.csv` registry.
4. **Optional Structured-Output LLM Fallback** — When deterministic rules return low confidence or ambiguity, optionally invokes **Gemini**, **OpenAI**, or local **Ollama** via typed `httpx` + Pydantic v2 structured output validation (no framework bloat).
5. **Source-Preserving Batch Export** — Exports original unmodified file bytes inside a ZIP archive with cross-platform filename sanitization and deterministic `(1)`, `(2)` collision numbering.

---

## Architecture

```
Next.js 15 (TypeScript + Tailwind)
        │  REST / multipart upload + JSON review state
        ▼
FastAPI (Python 3.12 + Pydantic v2)
  ├── SHA-256 duplicate fingerprint
  ├── PyMuPDF (digital text / page rasterization) + RapidOCR (ONNX)
  ├── Deterministic clause parser + bounded OSA company-list matcher
  ├── Optional LLM structured-output fallback (Gemini / OpenAI / Ollama)
  └── Source-preserving ZIP exporter (safe filename sanitization)
```

---

## Quick Start

### 1. Backend (Python + `uv`)

```powershell
cd backend
uv sync
uv run uvicorn app.main:app --reload --port 8000
```

Optional: copy `backend/.env.example` to `backend/.env` and configure `LLM_PROVIDER` (`gemini`, `openai`, or `ollama`) to enable the AI fallback stage. Without an API key, the app runs 100% locally in deterministic OCR + rules mode.

### 2. Frontend (Next.js + TypeScript)

```powershell
cd frontend
npm.cmd install
npm.cmd run dev
```

Open `http://localhost:3000`.

### 3. Tests & Evaluation Benchmark

```powershell
cd backend
uv run pytest
uv run python eval/run_eval.py
```

---

## Tech Stack

- **Frontend:** Next.js, React, TypeScript, Tailwind CSS
- **Backend:** Python 3.12, FastAPI, Pydantic v2, `httpx`, `PyMuPDF`, `RapidOCR (ONNX)`, `openpyxl`
- **Tooling:** `uv`, `pytest`, ESLint, TypeScript strict mode
