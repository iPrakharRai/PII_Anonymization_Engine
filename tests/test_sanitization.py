"""
Unit tests for Irreversible Sanitization Engine.
Validates true binary stream redaction, metadata eradication, and zero-leak guarantees.
"""
import io
import fitz
import pytest
from pathlib import Path
from backend.app.core.sanitization import SanitizationEngine


class TestSanitizationEngine:
    """Test suite for PDF redaction and binary stream sanitization."""

    def test_native_stream_redaction(self, tmp_path):
        # 1. Create a PDF in memory with sensitive content and metadata
        pdf_path = tmp_path / "sensitive_input.pdf"
        doc = fitz.open()
        page = doc.new_page(width=595, height=842)
        
        sensitive_aadhaar = "9988 7766 5544"
        sensitive_name = "Ramesh Chandra Sharma"
        secret_metadata_value = "TopSecretAuthorName"

        doc.set_metadata({
            "author": secret_metadata_value,
            "title": "Confidential Record",
            "subject": "Citizen PII Document"
        })

        # Insert text at specific coordinates
        page.insert_text((72, 110), sensitive_aadhaar, fontsize=12)
        page.insert_text((72, 160), sensitive_name, fontsize=12)
        doc.save(str(pdf_path))
        doc.close()

        # Verify sensitive text is present initially
        doc_initial = fitz.open(str(pdf_path))
        extracted_initial = doc_initial[0].get_text()
        assert sensitive_aadhaar in extracted_initial
        assert sensitive_name in extracted_initial
        assert doc_initial.metadata.get("author") == secret_metadata_value
        doc_initial.close()

        # 2. Apply SanitizationEngine
        doc_to_redact = fitz.open(str(pdf_path))
        boxes = [
            (70.0, 95.0, 255.0, 125.0),
            (70.0, 145.0, 305.0, 175.0)
        ]

        SanitizationEngine.apply_stream_redactions(
            page=doc_to_redact[0],
            bounding_boxes=boxes
        )
        SanitizationEngine.scrub_deep_metadata(doc_to_redact)

        sanitized_path = tmp_path / "sanitized_output.pdf"
        doc_to_redact.save(str(sanitized_path), garbage=4, deflate=True)
        doc_to_redact.close()

        # 3. Verification 1: Surface Text Extraction
        doc_sanitized = fitz.open(str(sanitized_path))
        extracted_sanitized = doc_sanitized[0].get_text()
        assert sensitive_aadhaar not in extracted_sanitized
        assert sensitive_name not in extracted_sanitized

        # 4. Verification 2: Metadata Eradication
        sanitized_meta = doc_sanitized.metadata
        for k, v in sanitized_meta.items():
            assert secret_metadata_value not in str(v)
            assert "Confidential" not in str(v)
        doc_sanitized.close()

        # 5. Verification 3: Raw Binary Stream Eradication
        with open(sanitized_path, "rb") as f:
            raw_bytes = f.read()

        assert sensitive_aadhaar.encode("utf-8") not in raw_bytes
        assert sensitive_name.encode("utf-8") not in raw_bytes
        assert secret_metadata_value.encode("utf-8") not in raw_bytes
