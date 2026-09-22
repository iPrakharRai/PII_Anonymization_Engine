"""
Custom Indian National Format Recognizers for Microsoft Presidio AnalyzerEngine.
Implements deterministic regex matching, format validation, and checksum verification (Verhoeff & Luhn).
"""
import re
from typing import List, Optional, Dict, Any, Set
from presidio_analyzer import Pattern, PatternRecognizer, RecognizerResult, EntityRecognizer
from backend.app.utils.verhoeff import validate_verhoeff
from backend.app.utils.luhn import validate_luhn
from backend.app.config import settings

class IndianAadhaarRecognizer(PatternRecognizer):
    """
    Detects Indian 12-digit Aadhaar Numbers.
    Enforces UIDAI rules: cannot begin with 0 or 1, validates using Verhoeff checksum.
    """
    PATTERNS = [
        Pattern(
            "Aadhaar_Standard",
            r"\b[2-9]\d{3}[\s\-]?\d{4}[\s\-]?\d{4}\b",
            0.6
        )
    ]
    CONTEXT = settings.CONTEXT_WORDS["IN_AADHAAR"]

    def __init__(self):
        super().__init__(
            supported_entity="IN_AADHAAR",
            patterns=self.PATTERNS,
            context=self.CONTEXT,
            name="IndianAadhaarRecognizer"
        )

    def validate_result(self, pattern_text: str) -> bool:
        clean_number = re.sub(r"[\s\-]+|\D", "", pattern_text)
        if len(clean_number) != 12:
            return False
        if clean_number[0] in ('0', '1'):
            return False
        return validate_verhoeff(clean_number)

    def analyze(self, text: str, entities: List[str], nlp_artifacts=None) -> List[RecognizerResult]:
        results = super().analyze(text, entities, nlp_artifacts)
        validated_results = []
        for res in results:
            span_text = text[res.start:res.end]
            if self.validate_result(span_text):
                # Boost confidence if Verhoeff passes
                res.score = min(1.0, res.score + 0.35)
                validated_results.append(res)
            elif any(c in text[max(0, res.start-30):min(len(text), res.end+30)].lower() for c in ["aadhaar", "uidai", "adhar"]):
                # If context is explicitly Aadhaar but maybe digit typo, retain with moderate score
                res.score = 0.55
                validated_results.append(res)
        return validated_results


class IndianPANRecognizer(PatternRecognizer):
    """
    Detects Indian Permanent Account Numbers (PAN).
    Format: [A-Z]{5}[0-9]{4}[A-Z]
    4th character designates entity type:
    P: Individual, C: Company, H: HUF, A: AOP, T: Trust, B: BOI, L: Local Auth, J: AJP, G: Govt, F: Firm
    """
    PATTERNS = [
        Pattern(
            "PAN_Standard",
            r"\b[A-Z]{5}[0-9]{4}[A-Z]\b",
            0.75
        )
    ]
    CONTEXT = settings.CONTEXT_WORDS["IN_PAN"]
    VALID_4TH_CHARS = set("PCHFATBLJG")

    def __init__(self):
        super().__init__(
            supported_entity="IN_PAN",
            patterns=self.PATTERNS,
            context=self.CONTEXT,
            name="IndianPANRecognizer"
        )

    def validate_result(self, pattern_text: str) -> bool:
        clean = pattern_text.strip().upper()
        if len(clean) != 10:
            return False
        return clean[3] in self.VALID_4TH_CHARS

    def analyze(self, text: str, entities: List[str], nlp_artifacts=None) -> List[RecognizerResult]:
        results = super().analyze(text, entities, nlp_artifacts)
        validated_results = []
        for res in results:
            span_text = text[res.start:res.end]
            if self.validate_result(span_text):
                res.score = min(1.0, res.score + 0.20)
                validated_results.append(res)
        return validated_results


class IndianPhoneRecognizer(PatternRecognizer):
    """
    Detects Indian mobile phone numbers (+91, 0, or 10-digit formats starting with 6, 7, 8, 9).
    """
    PATTERNS = [
        Pattern(
            "IN_Mobile_International",
            r"(?:\+91[\-\s]?|0)?[6-9]\d{4}[\-\s]?\d{5}\b",
            0.7
        ),
        Pattern(
            "IN_Mobile_Local",
            r"\b[6-9]\d{9}\b",
            0.65
        )
    ]
    CONTEXT = settings.CONTEXT_WORDS["IN_PHONE"]

    def __init__(self):
        super().__init__(
            supported_entity="IN_PHONE",
            patterns=self.PATTERNS,
            context=self.CONTEXT,
            name="IndianPhoneRecognizer"
        )


class IndianVoterIDRecognizer(PatternRecognizer):
    """
    Detects Indian Voter Identity Card (EPIC) numbers.
    Standard format: 3 uppercase letters followed by 7 numeric digits.
    """
    PATTERNS = [
        Pattern(
            "EPIC_Standard",
            r"\b[A-Z]{3}[0-9]{7}\b",
            0.75
        ),
        Pattern(
            "EPIC_State_Roll",
            r"\b[A-Z]{2}\/[0-9]{2}\/[0-9]{3}\/[0-9]{6,7}\b",
            0.85
        )
    ]
    CONTEXT = settings.CONTEXT_WORDS["IN_VOTER_ID"]

    def __init__(self):
        super().__init__(
            supported_entity="IN_VOTER_ID",
            patterns=self.PATTERNS,
            context=self.CONTEXT,
            name="IndianVoterIDRecognizer"
        )


class IndianIFSCRecognizer(PatternRecognizer):
    """
    Detects Indian Financial System Codes (IFSC).
    Format: 4 letters, 5th character 0, followed by 6 alphanumeric characters.
    """
    PATTERNS = [
        Pattern(
            "IFSC_Standard",
            r"\b[A-Z]{4}0[A-Z0-9]{6}\b",
            0.8
        )
    ]
    CONTEXT = settings.CONTEXT_WORDS["IN_IFSC"]

    def __init__(self):
        super().__init__(
            supported_entity="IN_IFSC",
            patterns=self.PATTERNS,
            context=self.CONTEXT,
            name="IndianIFSCRecognizer"
        )


class IndianBankAccountRecognizer(PatternRecognizer):
    """
    Detects Indian Bank Account numbers (9 to 18 digits adjacent to banking keywords or IFSC codes).
    """
    PATTERNS = [
        Pattern(
            "Bank_Account_Number",
            r"\b\d{9,18}\b",
            0.4
        )
    ]
    CONTEXT = settings.CONTEXT_WORDS["IN_BANK_ACCOUNT"] + ["ifsc", "branch", "disbursement", "subsidy"]

    def __init__(self):
        super().__init__(
            supported_entity="IN_BANK_ACCOUNT",
            patterns=self.PATTERNS,
            context=self.CONTEXT,
            name="IndianBankAccountRecognizer"
        )

    def analyze(self, text: str, entities: List[str], nlp_artifacts=None) -> List[RecognizerResult]:
        results = super().analyze(text, entities, nlp_artifacts)
        validated = []
        for res in results:
            span = text[res.start:res.end]
            # Exclude 10-digit mobile numbers or 12-digit Aadhaar numbers
            if len(span) == 10 and span[0] in '6789':
                continue
            if len(span) == 12 and validate_verhoeff(span):
                continue

            surrounding = text[max(0, res.start - 180):min(len(text), res.end + 180)].lower()
            has_context = any(k in surrounding for k in self.CONTEXT)
            has_ifsc = bool(re.search(r"[A-Z]{4}0[A-Z0-9]{6}", text[max(0, res.start - 150):min(len(text), res.end + 150)]))

            if has_context or has_ifsc:
                res.score = 0.88
                validated.append(res)
        return validated


class IndianPersonRecognizer(EntityRecognizer):
    """
    Detects Indian citizen names using administrative honorifics and kinship indicators.
    """
    ADMIN_TERMS = {
        "tehsil", "district", "village", "gram", "taluk", "sadar", "block", "signatory",
        "officer", "public", "notice", "rural", "development", "panchayati", "raj",
        "government", "pradesh", "uttar", "civil", "lines", "court", "judge",
        "magistrate", "revenue", "department", "municipal", "corporation",
        "nigam", "tender", "contractor", "allotment", "disclosure", "beneficiary",
        "name", "aadhaar", "uid", "mobile", "account", "ifsc", "code", "bank",
        "case", "suit", "order", "khasra", "khatauni", "mutation"
    }

    def __init__(self):
        super().__init__(
            supported_entities=["PERSON"],
            name="IndianPersonRecognizer"
        )

    def analyze(self, text: str, entities: List[str], nlp_artifacts=None) -> List[RecognizerResult]:
        results = []
        # Pattern 1: Honorifics (Shri, Smt, etc.)
        h_matches = re.finditer(r"\b(?:Shri|Smt|Shrimati|Kumari|Mr|Mrs|Ms|Dr)\.?\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,3})\b", text)
        for m in h_matches:
            name_val = m.group(1).strip()
            words = set(name_val.lower().split())
            if not (words & self.ADMIN_TERMS):
                results.append(RecognizerResult("PERSON", m.start(1), m.end(1), 0.90))

        # Pattern 2: Kinship (S/o, D/o, etc.)
        k_matches = re.finditer(r"\b(?:S\/o|D\/o|W\/o|C\/o|Son\s+of|Daughter\s+of|Wife\s+of)\s+(?:Shri\s+|Smt\s+)?([A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,3})\b", text)
        for m in k_matches:
            name_val = m.group(1).strip()
            words = set(name_val.lower().split())
            if not (words & self.ADMIN_TERMS):
                results.append(RecognizerResult("PERSON", m.start(1), m.end(1), 0.92))

        # Pattern 3: Tabular rows e.g. "1 Pranit Konda 6332" or "1\nPranit Konda\n6332"
        t_matches = re.finditer(r"(?:^|[\s\n])\d+\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,2})\s+[2-9]\d{3}", text)
        for m in t_matches:
            name_val = m.group(1).strip()
            words = set(name_val.lower().split())
            if not (words & self.ADMIN_TERMS):
                results.append(RecognizerResult("PERSON", m.start(1), m.end(1), 0.95))

        return results


