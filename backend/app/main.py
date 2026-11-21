from __future__ import annotations

import io
import json
import zipfile
from pathlib import Path
from typing import Annotated

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

from app.config import settings
from app.pipeline import SUPPORTED_EXTENSIONS, analyze_document_bytes
from app.rules import allocate_filename
from app.schemas import AnalyzeDocumentResponse, CompanyListResponse, HealthResponse
from app.xlsx_parser import parse_company_list

app = FastAPI(
    title="DocRename AI API",
    version="0.1.0",
    description="Hybrid local OCR + deterministic rules + structured-output LLM fallback API.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    return HealthResponse(
        ocr_engine="PyMuPDF + RapidOCR (ONNX)",
        llm_provider=settings.llm_provider,
        llm_configured=settings.llm_configured,
    )


@app.post("/api/company-list", response_model=CompanyListResponse)
async def upload_company_list(
    file: Annotated[UploadFile, File(...)],
) -> CompanyListResponse:
    filename = file.filename or "companies.xlsx"
    content = await file.read()
    if len(content) > settings.max_file_size_bytes:
        raise HTTPException(status_code=413, detail="Company list exceeds maximum file size.")
    try:
        companies = parse_company_list(filename, content)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return CompanyListResponse(count=len(companies), companies=companies, source_filename=filename)


@app.post("/api/analyze", response_model=AnalyzeDocumentResponse)
async def analyze_document(
    file: Annotated[UploadFile, File(...)],
    companies_json: Annotated[str, Form()] = "[]",
    use_llm_fallback: Annotated[bool, Form()] = True,
) -> AnalyzeDocumentResponse:
    filename = file.filename or "document.pdf"
    ext = Path(filename).suffix.lower()
    if ext not in SUPPORTED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type '{ext}'. Allowed: .pdf, .png, .jpg, .jpeg.",
        )

    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")
    if len(content) > settings.max_file_size_bytes:
        raise HTTPException(
            status_code=413,
            detail=f"File exceeds {settings.max_file_size_mb} MB limit.",
        )

    try:
        raw_companies = json.loads(companies_json)
        if not isinstance(raw_companies, list) or not all(
            isinstance(item, str) for item in raw_companies
        ):
            raise ValueError("companies_json must be a JSON array of strings.")
    except (json.JSONDecodeError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=f"Invalid companies_json: {exc}") from exc

    try:
        return await analyze_document_bytes(
            filename=filename,
            content=content,
            companies=raw_companies,
            use_llm_fallback=use_llm_fallback,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/api/export-zip")
async def export_zip(
    files: Annotated[list[UploadFile], File(...)],
    target_names_json: Annotated[str, Form()],
) -> StreamingResponse:
    """Package approved files into a ZIP archive, preserving exact original bytes."""
    try:
        target_names = json.loads(target_names_json)
        if not isinstance(target_names, list) or len(target_names) != len(files):
            raise ValueError("target_names_json must match the number of uploaded files.")
    except (json.JSONDecodeError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    archive_buffer = io.BytesIO()
    allocated_names: list[str] = []
    total_bytes = 0
    max_total_bytes = settings.max_file_size_bytes * 5

    with zipfile.ZipFile(archive_buffer, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
        for upload, desired_name in zip(files, target_names, strict=True):
            original = upload.filename or "document.pdf"
            ext = Path(original).suffix.lower()
            if ext not in SUPPORTED_EXTENSIONS:
                raise HTTPException(status_code=400, detail=f"Unsupported extension: {ext}")
            content = await upload.read()
            if len(content) > settings.max_file_size_bytes:
                raise HTTPException(
                    status_code=413,
                    detail=f"{original} exceeds {settings.max_file_size_mb} MB limit.",
                )
            total_bytes += len(content)
            if total_bytes > max_total_bytes:
                raise HTTPException(
                    status_code=413,
                    detail="Total batch export exceeds maximum size limit.",
                )
            try:
                final_name = allocate_filename(str(desired_name), ext, allocated_names)
            except ValueError as exc:
                raise HTTPException(status_code=400, detail=f"{original}: {exc}") from exc
            allocated_names.append(final_name)
            zf.writestr(final_name, content)

    archive_buffer.seek(0)
    return StreamingResponse(
        archive_buffer,
        media_type="application/zip",
        headers={"Content-Disposition": 'attachment; filename="renamed-documents.zip"'},
    )
