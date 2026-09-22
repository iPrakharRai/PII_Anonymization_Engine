"""
Unit tests for Custom Indian Entity Recognizers.
Validates pattern matching, checksum integration, and entity detection logic.
"""
import pytest
from backend.app.core.recognizers import (
    IndianAadhaarRecognizer,
    IndianPANRecognizer,
    IndianPhoneRecognizer,
    IndianVoterIDRecognizer,
    IndianIFSCRecognizer,
    IndianBankAccountRecognizer,
)
from backend.app.utils.verhoeff import generate_verhoeff


class TestIndianRecognizers:
    """Test suite for Presidio Indian recognizers."""

    def test_aadhaar_recognizer(self):
        rec = IndianAadhaarRecognizer()
        prefix = "89123456789"
        chk = generate_verhoeff(prefix)
        valid_aadhaar = f"{prefix[:4]} {prefix[4:8]} {prefix[8:]}{chk}"
        
        results = rec.analyze(text=f"Citizen Aadhaar card number is {valid_aadhaar}.", entities=["IN_AADHAAR"])
        assert len(results) >= 1
        assert results[0].entity_type == "IN_AADHAAR"
        assert results[0].score >= 0.85

    def test_pan_recognizer(self):
        rec = IndianPANRecognizer()
        # 4th character must be one of P, C, H, F, A, T, B, L, J, G
        text = "Permanent Account Number for applicant is ABCPE1234F."
        results = rec.analyze(text=text, entities=["IN_PAN"])
        assert len(results) >= 1
        assert results[0].entity_type == "IN_PAN"
        assert results[0].score >= 0.85

    def test_phone_recognizer(self):
        rec = IndianPhoneRecognizer()
        valid_phones = [
            "Contact applicant at +91 9876543210 immediately.",
            "Phone: 8123456789.",
            "Mobile: 7012345678."
        ]
        for t in valid_phones:
            results = rec.analyze(text=t, entities=["IN_PHONE"])
            assert len(results) >= 1
            assert results[0].entity_type == "IN_PHONE"

    def test_ifsc_recognizer(self):
        rec = IndianIFSCRecognizer()
        text = "Transfer DBT funds to SBIN0001234 for processing."
        results = rec.analyze(text=text, entities=["IN_IFSC"])
        assert len(results) >= 1
        assert results[0].entity_type == "IN_IFSC"
        assert results[0].score >= 0.80

    def test_voter_id_recognizer(self):
        rec = IndianVoterIDRecognizer()
        text = "Voter EPIC reference: WXY1234567 issued at Lucknow."
        results = rec.analyze(text=text, entities=["IN_VOTER_ID"])
        assert len(results) >= 1
        assert results[0].entity_type == "IN_VOTER_ID"

    def test_bank_account_recognizer(self):
        rec = IndianBankAccountRecognizer()
        text = "Direct credit to Account No: 123456789012 for pension payment."
        results = rec.analyze(text=text, entities=["IN_BANK_ACCOUNT"])
        assert len(results) >= 1
        assert results[0].entity_type == "IN_BANK_ACCOUNT"
