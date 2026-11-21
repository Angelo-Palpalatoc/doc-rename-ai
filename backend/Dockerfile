FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_LINK_MODE=copy

RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 \
    libglib2.0-0 \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app

COPY pyproject.toml uv.lock* ./
RUN uv sync --frozen --no-dev || uv sync --no-dev

COPY app ./app
COPY eval ./eval

# Pre-warm RapidOCR English ONNX models during image build to avoid cold-start downloads
RUN uv run python -c "from app.ocr import _get_rapidocr; _get_rapidocr()"

# Support Hugging Face Spaces (7860), Render/Railway ($PORT), and local Docker (8000)
ENV PORT=7860
EXPOSE 7860

CMD ["sh", "-c", "uv run uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-7860}"]
