"""
Throughput & Resource Efficiency Profiler.
Measures latency per page, memory consumption, and batch processing throughput (pages/min)
for both born-digital PDFs and scanned raster circulars.
"""
import time
import json
import os
from pathlib import Path
import fitz
import psutil

import sys
BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from backend.app.core.pipeline import RedactionPipeline

BENCHMARK_DIR = BASE_DIR / "data" / "synthetic_benchmark"
PROFILE_REPORT = BENCHMARK_DIR / "latency_profile_report.json"

def profile_system():
    print("=" * 70)
    print("THROUGHPUT, LATENCY & RESOURCE EFFICIENCY PROFILING")
    print("=" * 70)

    pipeline = RedactionPipeline()
    process = psutil.Process(os.getpid())

    # 1. Digital PDF Profiling
    digital_files = list(BENCHMARK_DIR.glob("mock_doc_*.pdf"))[:20]
    t0 = time.time()
    mem_start = process.memory_info().rss / (1024 * 1024)

    digital_pages = 0
    for f in digital_files:
        doc = fitz.open(str(f))
        digital_pages += len(doc)
        doc.close()
        pipeline.process_document(f)

    digital_elapsed = time.time() - t0
    mem_peak_digital = process.memory_info().rss / (1024 * 1024)
    avg_digital_latency = digital_elapsed / max(1, digital_pages)
    digital_ppm = (digital_pages / digital_elapsed) * 60.0

    print(f"Digital Documents Processed: {len(digital_files)} files ({digital_pages} pages)")
    print(f"Digital Latency / Page:      {avg_digital_latency:.4f}s (Target: < 1.8s)")
    print(f"Digital Throughput:          {digital_ppm:.1f} pages / minute")
    print(f"Memory (RAM) Footprint:      {mem_peak_digital:.1f} MB (Delta: +{mem_peak_digital - mem_start:.1f} MB)")
    print("-" * 70)

    # 2. Simulated Scanned Document Profiling (Rasterized at 200 DPI)
    scanned_pages = 0
    scanned_files = []
    scanned_dir = BENCHMARK_DIR / "scanned_samples"
    scanned_dir.mkdir(exist_ok=True)

    # Create 3 rasterized scanned PDF samples
    for idx, f in enumerate(digital_files[:3]):
        doc_src = fitz.open(str(f))
        doc_dst = fitz.open()
        for p in doc_src:
            pix = p.get_pixmap(dpi=200)
            img_bytes = pix.tobytes("png")
            page_dst = doc_dst.new_page(width=p.rect.width, height=p.rect.height)
            page_dst.insert_image(p.rect, stream=img_bytes)
        scan_path = scanned_dir / f"scanned_{f.name}"
        doc_dst.save(str(scan_path))
        doc_dst.close()
        doc_src.close()
        scanned_files.append(scan_path)

    t0_scan = time.time()
    for sf in scanned_files:
        doc = fitz.open(str(sf))
        scanned_pages += len(doc)
        doc.close()
        pipeline.process_document(sf)

    scan_elapsed = time.time() - t0_scan
    avg_scan_latency = scan_elapsed / max(1, scanned_pages)
    scan_ppm = (scanned_pages / scan_elapsed) * 60.0
    mem_peak_scan = process.memory_info().rss / (1024 * 1024)

    print(f"Scanned Raster Documents:    {len(scanned_files)} files ({scanned_pages} pages)")
    print(f"Scanned Latency / Page:      {avg_scan_latency:.4f}s (Target: < 4.5s)")
    print(f"Scanned Throughput:          {scan_ppm:.1f} pages / minute")
    print(f"Peak Memory Footprint:       {mem_peak_scan:.1f} MB")
    print("=" * 70)

    report = {
        "digital": {
            "pages_tested": digital_pages,
            "latency_per_page_seconds": round(avg_digital_latency, 4),
            "throughput_pages_per_minute": round(digital_ppm, 1),
            "target_latency_seconds": 1.8,
            "target_met": bool(avg_digital_latency < 1.8)
        },
        "scanned": {
            "pages_tested": scanned_pages,
            "latency_per_page_seconds": round(avg_scan_latency, 4),
            "throughput_pages_per_minute": round(scan_ppm, 1),
            "target_latency_seconds": 4.5,
            "target_met": bool(avg_scan_latency < 4.5)
        },
        "memory_mb": {
            "baseline": round(mem_start, 1),
            "peak_digital": round(mem_peak_digital, 1),
            "peak_scanned": round(mem_peak_scan, 1)
        }
    }

    with open(PROFILE_REPORT, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    print(f"Profiler report written to {PROFILE_REPORT}")

if __name__ == "__main__":
    profile_system()
