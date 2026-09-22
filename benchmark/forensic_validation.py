"""
Forensic Security Validation & Zero-Leak Verification Test Suite.
Performs raw binary stream inspection and text search across sanitized PDF files.
Verifies 100% eradication of sensitive tokens (no copy-paste leaks, no raw stream remnants).
"""
import json
import re
from pathlib import Path
import fitz

import sys
BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from backend.app.core.pipeline import RedactionPipeline
from backend.app.core.sanitization import SanitizationEngine

BENCHMARK_DIR = BASE_DIR / "data" / "synthetic_benchmark"
GROUND_TRUTH_FILE = BENCHMARK_DIR / "ground_truth.json"
REPORT_FILE = BENCHMARK_DIR / "forensic_security_report.json"

def run_forensic_validation(sample_size: int = 20):
    print("=" * 70)
    print("FORENSIC SECURITY VALIDATION: ZERO-LEAK STREAM & BINARY VERIFICATION")
    print("=" * 70)

    with open(GROUND_TRUTH_FILE, "r", encoding="utf-8") as f:
        ground_truth = json.load(f)

    pipeline = RedactionPipeline()
    test_subset = ground_truth[:sample_size]

    total_tokens_tested = 0
    text_extraction_leaks = 0
    raw_binary_stream_leaks = 0
    metadata_leaks = 0

    doc_results = []

    for idx, meta in enumerate(test_subset):
        orig_pdf_path = BENCHMARK_DIR / meta["filename"]
        truth_entities = meta["truth_entities"]

        # Run pipeline to sanitize
        res = pipeline.process_document(orig_pdf_path, confidence_threshold=0.65)
        sanitized_pdf_path = Path(res["sanitized_file"])

        sanitized_doc = fitz.open(str(sanitized_pdf_path))

        # 1. Level 1: Text extraction verification
        extracted_text = ""
        for page in sanitized_doc:
            extracted_text += page.get_text("text") + " "

        # 2. Level 2: Raw Binary Content Stream Inspection
        with open(sanitized_pdf_path, "rb") as f_bin:
            raw_pdf_bytes = f_bin.read()

        # Decompressed stream bytes
        decompressed_stream_bytes = bytearray()
        for xref in range(1, sanitized_doc.xref_length()):
            try:
                stream_data = sanitized_doc.xref_stream(xref)
                if stream_data:
                    decompressed_stream_bytes.extend(stream_data)
            except Exception:
                pass

        doc_leaks = []

        for item in truth_entities:
            raw_val = item["text"].strip()
            if not raw_val:
                continue

            total_tokens_tested += 1

            # Test A: Text level leak
            clean_val = re.sub(r'[\s\-]+', '', raw_val)
            clean_extracted = re.sub(r'[\s\-]+', '', extracted_text)
            if clean_val in clean_extracted:
                text_extraction_leaks += 1
                doc_leaks.append({"type": "text_extract", "token": raw_val})

            # Test B: Raw byte stream search
            token_bytes = raw_val.encode('utf-8')
            clean_bytes = clean_val.encode('utf-8')

            if (token_bytes in raw_pdf_bytes) or (clean_bytes in raw_pdf_bytes) or \
               (token_bytes in decompressed_stream_bytes) or (clean_bytes in decompressed_stream_bytes):
                raw_binary_stream_leaks += 1
                doc_leaks.append({"type": "raw_binary_stream", "token": raw_val})

        # Test C: Metadata inspection
        meta_dict = sanitized_doc.metadata or {}
        for k, v in meta_dict.items():
            if any(item["text"].lower() in str(v).lower() for item in truth_entities):
                metadata_leaks += 1

        sanitized_doc.close()

        doc_results.append({
            "filename": meta["filename"],
            "tokens_checked": len(truth_entities),
            "leaks_detected": len(doc_leaks),
            "leak_details": doc_leaks
        })

    # Summary
    success = (text_extraction_leaks == 0) and (raw_binary_stream_leaks == 0) and (metadata_leaks == 0)
    eradication_rate = 100.0 if total_tokens_tested > 0 else 0.0
    if total_tokens_tested > 0:
        eradication_rate = ((total_tokens_tested - (text_extraction_leaks + raw_binary_stream_leaks)) / total_tokens_tested) * 100.0

    print(f"Total Sensitive Tokens Verified: {total_tokens_tested}")
    print(f"Level 1: High-Level Text Extraction Leaks: {text_extraction_leaks}")
    print(f"Level 2: Raw Binary Content Stream Leaks:  {raw_binary_stream_leaks}")
    print(f"Level 3: Metadata / XMP Dictionary Leaks:  {metadata_leaks}")
    print(f"Forensic Eradication Rate: {eradication_rate:.2f}%")
    print("=" * 70)
    if success:
        print("PASS: 100% Zero-Leak Forensic Eradication Confirmed!")
    else:
        print("FAIL: Leaks detected in sanitized output!")
    print("=" * 70)

    report = {
        "sample_size": sample_size,
        "total_tokens_tested": total_tokens_tested,
        "text_extraction_leaks": text_extraction_leaks,
        "raw_binary_stream_leaks": raw_binary_stream_leaks,
        "metadata_leaks": metadata_leaks,
        "eradication_rate_percent": eradication_rate,
        "zero_leak_verified": success,
        "doc_results": doc_results
    }

    with open(REPORT_FILE, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    print(f"Forensic security report saved to {REPORT_FILE}")
    return success

if __name__ == "__main__":
    run_forensic_validation(sample_size=25)
