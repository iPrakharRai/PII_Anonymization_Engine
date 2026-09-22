"""
Unit tests for DPDP Act 2023 Tamper-Evident Audit Compliance.
Enforces the Zero-Plaintext PII storage guarantee and verifies cryptographic integrity hashing.
"""
import json
import pytest
from pathlib import Path
from backend.app.core.audit import AuditLogger


class TestAuditCompliance:
    """Test suite ensuring strict compliance with zero-plaintext PII audit principles."""

    def test_zero_plaintext_pii_in_audit_record(self, tmp_path):
        orig_file = tmp_path / "orig.pdf"
        san_file = tmp_path / "san.pdf"
        orig_file.write_bytes(b"dummy original content")
        san_file.write_bytes(b"dummy sanitized content")

        plain_aadhaar = "9988 7766 5544"
        plain_name = "Vikram Aditya Singh"
        plain_phone = "9876543210"

        redactions_by_page = {
            0: [
                {"entity_type": "IN_AADHAAR", "text": plain_aadhaar, "confidence": 0.98, "bbox": [10, 10, 50, 20]},
                {"entity_type": "PERSON", "text": plain_name, "confidence": 0.92, "bbox": [10, 30, 50, 40]},
                {"entity_type": "IN_PHONE", "text": plain_phone, "confidence": 0.95, "bbox": [10, 50, 50, 60]},
            ]
        }

        audit_record = AuditLogger.generate_audit_log(
            original_path=orig_file,
            sanitized_path=san_file,
            redactions_by_page=redactions_by_page
        )

        audit_json_str = json.dumps(audit_record)

        # Assert: STRICT ZERO-PLAINTEXT RULE
        assert plain_aadhaar not in audit_json_str, "Plaintext Aadhaar found in audit log!"
        assert plain_name not in audit_json_str, "Plaintext Name found in audit log!"
        assert plain_phone not in audit_json_str, "Plaintext Phone found in audit log!"

        # Assert: SHA-256 token digests are present instead of raw text
        assert "SHA256:" in audit_json_str

    def test_audit_cryptographic_integrity_structure(self, tmp_path):
        orig_file = tmp_path / "orig.pdf"
        san_file = tmp_path / "san.pdf"
        orig_file.write_bytes(b"content_a")
        san_file.write_bytes(b"content_b")

        audit_record = AuditLogger.generate_audit_log(
            original_path=orig_file,
            sanitized_path=san_file,
            redactions_by_page={}
        )

        assert "file_manifest" in audit_record
        assert "original_sha256" in audit_record["file_manifest"]
        assert "sanitized_sha256" in audit_record["file_manifest"]
        assert audit_record["redaction_summary"]["total_entities_redacted"] == 0
        assert audit_record["file_manifest"]["original_sha256"] != audit_record["file_manifest"]["sanitized_sha256"]
