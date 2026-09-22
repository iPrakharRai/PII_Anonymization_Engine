"""
FastAPI REST API Routes.
"""
import shutil
from pathlib import Path
from typing import Optional, Dict, Any, List
from fastapi import APIRouter, UploadFile, File, HTTPException, Query, Body
from fastapi.responses import FileResponse, JSONResponse
import fitz

from backend.app.config import settings, INPUT_DIR, OUTPUT_DIR, AUDIT_DIR
from backend.app.api.models import (
    DocumentAnalysisResponse,
    PageAnalysisModel,
    EntitySpanModel,
    RedactionApplyRequest,
    RedactionResponse,
    HealthResponse
)
from backend.app.core.pipeline import RedactionPipeline
from backend.app.core.ingestion import DocumentIngestionEngine
from backend.app.core.sanitization import SanitizationEngine
from backend.app.core.audit import AuditLogger

router = APIRouter(prefix="/api/v1", tags=["PII Redaction & Compliance"])

# Initialize pipeline instance
pipeline = RedactionPipeline()

@router.get("/health", response_model=HealthResponse)
async def health_check():
    return HealthResponse(
        status="healthy",
        engine_version=settings.VERSION,
        compliance=settings.COMPLIANCE_STANDARD,
        models_loaded={
            "spacy": pipeline.analyzer.nlp is not None,
            "presidio": pipeline.analyzer.analyzer is not None,
            "indian_recognizers": True
        }
    )

@router.post("/upload")
async def upload_document(file: UploadFile = File(...)):
    """Uploads a PDF or image document for processing."""
    if not (file.filename.lower().endswith(".pdf") or file.filename.lower().endswith(('.png', '.jpg', '.jpeg', '.tiff'))):
        raise HTTPException(status_code=400, detail="Unsupported file format. Please upload PDF or image documents.")

    save_path = INPUT_DIR / file.filename
    with open(save_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    return {
        "filename": file.filename,
        "file_size": save_path.stat().st_size,
        "status": "uploaded",
        "path": str(save_path)
    }

@router.post("/analyze", response_model=DocumentAnalysisResponse)
async def analyze_document(
    filename: str = Body(..., embed=True),
    confidence_threshold: float = Body(0.70, embed=True)
):
    """
    Performs dual-engine layout analysis and hybrid PII identification.
    Returns detected bounding boxes for operator review.
    """
    file_path = INPUT_DIR / filename
    if not file_path.exists():
        raise HTTPException(status_code=404, detail=f"File '{filename}' not found. Please upload it first.")

    doc = fitz.open(str(file_path))
    pages_result = []
    total_entities = 0

    import time
    start_t = time.time()

    for page_idx in range(len(doc)):
        page = doc[page_idx]
        ingest_res = DocumentIngestionEngine.ingest_page(page)
        raw_entities = pipeline.analyzer.analyze_text(ingest_res["full_text"])

        filtered = [e for e in raw_entities if e["score"] >= confidence_threshold]
        aligned_boxes = pipeline.align_entities_to_bboxes(filtered, ingest_res["tokens"])

        entity_models = [
            EntitySpanModel(
                entity_type=b["entity_type"],
                score=b["score"],
                text=b.get("text"),
                bbox=b["bbox"],
                start=b.get("start"),
                end=b.get("end"),
                is_approved=True
            )
            for b in aligned_boxes
        ]
        total_entities += len(entity_models)

        pages_result.append(
            PageAnalysisModel(
                page_num=page_idx + 1,
                is_digital=ingest_res["is_digital"],
                engine=ingest_res["engine"],
                detected_entities=entity_models,
                raw_token_count=len(ingest_res["tokens"]),
                text_snippet=ingest_res["full_text"][:300]
            )
        )

    doc.close()
    elapsed = round(time.time() - start_t, 3)

    return DocumentAnalysisResponse(
        success=True,
        original_file=filename,
        page_count=len(pages_result),
        total_entities_detected=total_entities,
        elapsed_seconds=elapsed,
        pages=pages_result
    )

@router.post("/redact", response_model=RedactionResponse)
async def apply_redactions_endpoint(req: RedactionApplyRequest):
    """
    Executes true stream redaction, pixel burn-in, metadata scrubbing,
    and produces tamper-evident audit log.
    """
    file_path = INPUT_DIR / req.filename
    if not file_path.exists():
        raise HTTPException(status_code=404, detail=f"File '{req.filename}' not found.")

    # Format manual overrides if passed
    manual_overrides = None
    if req.overrides_by_page:
        manual_overrides = {}
        for p_str, items in req.overrides_by_page.items():
            p_idx = int(p_str) - 1  # Convert to 0-indexed
            # Filter only approved items
            approved = [item.dict() for item in items if item.is_approved]
            manual_overrides[p_idx] = approved

    result = pipeline.process_document(
        file_path=file_path,
        confidence_threshold=req.confidence_threshold,
        manual_overrides=manual_overrides
    )

    return RedactionResponse(
        success=result["success"],
        original_file=req.filename,
        sanitized_file=Path(result["sanitized_file"]).name,
        audit_file=Path(result["audit_file"]).name,
        page_count=result["page_count"],
        total_redactions=result["total_redactions"],
        elapsed_seconds=result["elapsed_seconds"],
        audit_summary=result["audit_summary"]
    )

@router.get("/download/sanitized/{filename}")
async def download_sanitized(filename: str):
    path = OUTPUT_DIR / filename
    if not path.exists():
        raise HTTPException(status_code=404, detail="Sanitized file not found.")
    return FileResponse(path=path, filename=filename, media_type="application/pdf")

@router.get("/download/audit/{filename}")
async def download_audit(filename: str):
    path = AUDIT_DIR / filename
    if not path.exists():
        raise HTTPException(status_code=404, detail="Audit log not found.")
    return FileResponse(path=path, filename=filename, media_type="application/json")
