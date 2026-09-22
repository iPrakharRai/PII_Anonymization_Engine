"""
Pydantic v2 API Schemas.
"""
from typing import List, Dict, Any, Optional, Tuple
from pydantic import BaseModel, Field

class EntitySpanModel(BaseModel):
    entity_type: str = Field(..., description="Category of detected PII, e.g. IN_AADHAAR, IN_PAN, PERSON")
    score: float = Field(..., description="Detection confidence score between 0.0 and 1.0")
    text: Optional[str] = Field(None, description="Plaintext snippet for UI review prior to sanitization")
    bbox: Tuple[float, float, float, float] = Field(..., description="Universal page bounding box (x0, y0, x1, y1)")
    start: Optional[int] = None
    end: Optional[int] = None
    is_approved: bool = Field(True, description="Approval toggle status from operator review")

class PageAnalysisModel(BaseModel):
    page_num: int
    is_digital: bool
    engine: str
    detected_entities: List[EntitySpanModel]
    raw_token_count: int
    text_snippet: str

class DocumentAnalysisResponse(BaseModel):
    success: bool
    original_file: str
    page_count: int
    total_entities_detected: int
    elapsed_seconds: float
    pages: List[PageAnalysisModel]

class RedactionApplyRequest(BaseModel):
    filename: str
    confidence_threshold: float = Field(0.70, ge=0.0, le=1.0)
    overrides_by_page: Optional[Dict[int, List[EntitySpanModel]]] = None

class RedactionResponse(BaseModel):
    success: bool
    original_file: str
    sanitized_file: str
    audit_file: str
    page_count: int
    total_redactions: int
    elapsed_seconds: float
    audit_summary: Dict[str, Any]

class HealthResponse(BaseModel):
    status: str
    engine_version: str
    compliance: str
    models_loaded: Dict[str, bool]
