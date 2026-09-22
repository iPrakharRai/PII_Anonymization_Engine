"""
Complete End-to-End Processing Pipeline.
Integrates Ingestion -> Spatial Alignment -> Hybrid Analysis -> Redaction -> Audit.
"""
from typing import Dict, List, Any, Tuple, Optional
from pathlib import Path
import fitz
import time

from backend.app.core.ingestion import DocumentIngestionEngine
from backend.app.core.analyzer import PIIAnalyzer
from backend.app.core.sanitization import SanitizationEngine
from backend.app.core.audit import AuditLogger
from backend.app.config import settings, OUTPUT_DIR, AUDIT_DIR

class RedactionPipeline:
    """
    High-level orchestrator for analyzing and sanitizing public documents.
    """
    def __init__(self):
        self.analyzer = PIIAnalyzer()

    def align_entities_to_bboxes(
        self,
        entities: List[Dict[str, Any]],
        token_spans: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Maps entity character ranges (start, end) in the page's synthesized text
        back to exact token bounding boxes on the PDF page canvas.
        Handles multi-token and multi-line entities properly.
        """
        aligned = []
        for ent in entities:
            e_start = ent["start"]
            e_end = ent["end"]

            # Find matching tokens
            matched_tokens = [
                t for t in token_spans
                if not (t["end_char"] <= e_start or t["start_char"] >= e_end)
            ]

            if not matched_tokens:
                continue

            # Group by line/block to prevent cross-line bounding box inflation
            line_groups = {}
            for t in matched_tokens:
                line_id = t.get("line_no", 0)
                line_groups.setdefault(line_id, []).append(t)

            for line_id, line_tokens in line_groups.items():
                xs0 = [t["bbox"][0] for t in line_tokens]
                ys0 = [t["bbox"][1] for t in line_tokens]
                xs1 = [t["bbox"][2] for t in line_tokens]
                ys1 = [t["bbox"][3] for t in line_tokens]

                union_bbox = (min(xs0), min(ys0), max(xs1), max(ys1))

                aligned.append({
                    "entity_type": ent["entity_type"],
                    "score": ent["score"],
                    "text": ent["text"],
                    "bbox": union_bbox,
                    "start": e_start,
                    "end": e_end
                })

        return aligned

    def process_document(
        self,
        file_path: Path,
        confidence_threshold: float = 0.70,
        manual_overrides: Optional[Dict[int, List[Dict[str, Any]]]] = None
    ) -> Dict[str, Any]:
        """
        Executes full pipeline:
        1. Ingests all pages (auto-routes digital vs scanned)
        2. Detects PII with hybrid analyzer & boosts contextual scores
        3. Harmonizes spatial bounding boxes
        4. Applies sanitization (or uses manual review toggles if provided)
        5. Generates DPDP-compliant tamper-evident audit log
        """
        start_time = time.time()
        doc = fitz.open(str(file_path))
        page_count = len(doc)

        analysis_pages = []
        redactions_by_page = {}
        is_any_page_scanned = False

        for page_idx in range(page_count):
            page = doc[page_idx]
            ingest_result = DocumentIngestionEngine.ingest_page(page)

            if not ingest_result["is_digital"]:
                is_any_page_scanned = True

            # Hybrid PII detection
            raw_entities = self.analyzer.analyze_text(ingest_result["full_text"])

            # Filter by confidence threshold
            filtered_entities = [
                e for e in raw_entities
                if e["score"] >= confidence_threshold
            ]

            # Spatial alignment to bounding boxes
            aligned_boxes = self.align_entities_to_bboxes(
                entities=filtered_entities,
                token_spans=ingest_result["tokens"]
            )

            # Check if manual overrides exist for this page
            if manual_overrides and page_idx in manual_overrides:
                final_boxes = manual_overrides[page_idx]
            else:
                final_boxes = aligned_boxes

            redactions_by_page[page_idx] = final_boxes

            analysis_pages.append({
                "page_num": page_idx + 1,
                "engine": ingest_result["engine"],
                "is_digital": ingest_result["is_digital"],
                "detected_entities": final_boxes,
                "raw_token_count": len(ingest_result["tokens"]),
                "text_snippet": ingest_result["full_text"][:300]
            })

        # Generate output sanitized PDF
        sanitized_filename = f"sanitized_{file_path.stem}.pdf"
        sanitized_path = OUTPUT_DIR / sanitized_filename

        total_redactions, cleaned_meta = SanitizationEngine.sanitize_document(
            doc=doc,
            redactions_by_page=redactions_by_page,
            is_scanned_doc=is_any_page_scanned
        )

        SanitizationEngine.save_sanitized_document(doc, sanitized_path)
        doc.close()

        elapsed = round(time.time() - start_time, 3)

        # Generate Audit Log
        audit_filename = f"audit_{file_path.stem}.json"
        audit_path = AUDIT_DIR / audit_filename
        audit_data = AuditLogger.generate_audit_log(
            original_path=file_path,
            sanitized_path=sanitized_path,
            redactions_by_page=redactions_by_page,
            processing_metadata={
                "page_count": page_count,
                "elapsed_seconds": elapsed,
                "latency_per_page": round(elapsed / max(1, page_count), 3),
                "is_scanned_doc": is_any_page_scanned,
                "confidence_threshold": confidence_threshold
            }
        )
        AuditLogger.save_audit_log(audit_data, audit_path)

        return {
            "success": True,
            "original_file": str(file_path),
            "sanitized_file": str(sanitized_path),
            "audit_file": str(audit_path),
            "page_count": page_count,
            "total_redactions": total_redactions,
            "elapsed_seconds": elapsed,
            "pages": analysis_pages,
            "audit_summary": audit_data["redaction_summary"]
        }
