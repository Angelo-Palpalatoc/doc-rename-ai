from __future__ import annotations

import asyncio
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.matcher import normalize_company_name
from app.ocr import OCRResult
from app.pipeline import analyze_document_bytes


async def main() -> int:
    dataset_path = Path(__file__).parent / "dataset.json"
    cases = json.loads(dataset_path.read_text(encoding="utf-8"))

    passed = 0
    total_ms = 0.0

    print(f"Running DocRename AI evaluation on {len(cases)} benchmark cases...\n")
    print(f"{'ID':<22} {'STATUS':<8} {'METHOD':<20} {'CONF':<6} {'LATENCY':<8}")
    print("-" * 70)

    for case in cases:
        t0 = time.perf_counter()
        result = await analyze_document_bytes(
            filename=f"{case['id']}.pdf",
            content=case["text"].encode("utf-8"),
            companies=case["companies"],
            use_llm_fallback=False,
            ocr_override=OCRResult(text=case["text"], page_count=1, source="pdf_text"),
        )
        elapsed_ms = (time.perf_counter() - t0) * 1000
        total_ms += elapsed_ms

        expected = case["expected_name"]
        expected_ambiguous = case["expected_ambiguous"]

        if expected is None:
            ok = result.suggested_name is None and result.ambiguous == expected_ambiguous
        else:
            ok = result.suggested_name is not None and (
                normalize_company_name(result.suggested_name) == normalize_company_name(expected)
            )

        if ok:
            passed += 1
        status = "PASS" if ok else "FAIL"
        print(
            f"{case['id']:<22} {status:<8} {result.method:<20} "
            f"{result.confidence:<6.2f} {elapsed_ms:>6.2f}ms"
        )
        if not ok:
            print(f"   Expected: {expected!r} (ambiguous={expected_ambiguous})")
            print(f"   Got:      {result.suggested_name!r} (ambiguous={result.ambiguous})")

    accuracy = (passed / len(cases)) * 100 if cases else 0.0
    print("-" * 70)
    print(
        f"Accuracy: {passed}/{len(cases)} ({accuracy:.1f}%) | Avg latency: {total_ms / len(cases):.2f}ms"
    )
    return 0 if passed == len(cases) else 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
