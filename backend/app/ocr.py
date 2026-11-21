from __future__ import annotations

import io
import threading
from dataclasses import dataclass
from typing import Literal

import pymupdf
from PIL import Image, ImageOps

_ocr_engine = None
_ocr_lock = threading.Lock()
MAX_PDF_PAGES = 30
MAX_IMAGE_LONG_EDGE = 2400
PDF_RENDER_LONG_EDGE = 2000


@dataclass(frozen=True)
class OCRResult:
    text: str
    page_count: int
    source: Literal["pdf_text", "rapidocr", "hybrid"]


def _get_rapidocr():
    global _ocr_engine
    if _ocr_engine is None:
        with _ocr_lock:
            if _ocr_engine is None:
                from rapidocr import LangRec, ModelType, OCRVersion, RapidOCR

                _ocr_engine = RapidOCR(
                    params={
                        "Rec.lang_type": LangRec.EN,
                        "Rec.ocr_version": OCRVersion.PPOCRV4,
                        "Rec.model_type": ModelType.MOBILE,
                        "Det.limit_side_len": 1600,
                    }
                )
    return _ocr_engine


def _run_rapidocr_on_bytes(image_bytes: bytes) -> str:
    engine = _get_rapidocr()
    result = engine(image_bytes)
    if not result or not result.txts:
        return ""
    lines = [str(text).strip() for text in result.txts if str(text).strip()]
    return "\n".join(lines)


def extract_document_text(content: bytes, extension: str) -> OCRResult:
    """Extract text from PDF, PNG, or JPG bytes.

    Uses embedded PDF text when cleanly present, and renders scanned/image pages
    at ~2000px long edge through RapidOCR's English PP-OCRv4 model (preserving
    Latin word spacing). Pages are separated by form-feed (`\\f`).
    """
    ext = extension.lower()
    if ext == ".pdf":
        return _extract_pdf(content)
    if ext in {".png", ".jpg", ".jpeg"}:
        return _extract_image(content)
    raise ValueError(f"Unsupported document extension: {extension}")


def _extract_pdf(content: bytes) -> OCRResult:
    doc = pymupdf.open(stream=content, filetype="pdf")
    try:
        pages_text: list[str] = []
        used_text = False
        used_ocr = False
        max_pages = min(len(doc), MAX_PDF_PAGES)

        for idx in range(max_pages):
            page = doc[idx]
            embedded = page.get_text("text").strip()
            has_images = bool(page.get_images(full=False))

            # Trust embedded text when substantial and not merely a watermark over a scanned image.
            if len(embedded) >= 60 and not (has_images and len(embedded) < 200):
                pages_text.append(embedded)
                used_text = True
            else:
                long_edge = max(page.rect.width, page.rect.height, 1.0)
                scale = min(max(PDF_RENDER_LONG_EDGE / long_edge, 1.5), 3.5)
                pix = page.get_pixmap(matrix=pymupdf.Matrix(scale, scale), alpha=False)
                ocr_text = _run_rapidocr_on_bytes(pix.tobytes("png"))
                pages_text.append(ocr_text if ocr_text else embedded)
                used_ocr = True

        source: Literal["pdf_text", "rapidocr", "hybrid"]
        if used_text and used_ocr:
            source = "hybrid"
        elif used_ocr:
            source = "rapidocr"
        else:
            source = "pdf_text"

        return OCRResult(
            text="\f".join(pages_text),
            page_count=len(doc),
            source=source,
        )
    finally:
        doc.close()


def _extract_image(content: bytes) -> OCRResult:
    with Image.open(io.BytesIO(content)) as img:
        oriented = ImageOps.exif_transpose(img).convert("RGB")
        w, h = oriented.size
        long_edge = max(w, h)
        if long_edge > MAX_IMAGE_LONG_EDGE:
            ratio = MAX_IMAGE_LONG_EDGE / long_edge
            oriented = oriented.resize(
                (max(1, int(w * ratio)), max(1, int(h * ratio))),
                Image.Resampling.LANCZOS,
            )
        buf = io.BytesIO()
        oriented.save(buf, format="PNG")
        text = _run_rapidocr_on_bytes(buf.getvalue())
    return OCRResult(text=text, page_count=1, source="rapidocr")
