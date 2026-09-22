import os
from pathlib import Path
from pydantic import BaseModel
from typing import Dict, List

BASE_DIR = Path(__file__).resolve().parent.parent.parent
DATA_DIR = BASE_DIR / "data"
INPUT_DIR = DATA_DIR / "input"
OUTPUT_DIR = DATA_DIR / "output"
AUDIT_DIR = DATA_DIR / "audit"

for d in [DATA_DIR, INPUT_DIR, OUTPUT_DIR, AUDIT_DIR]:
    d.mkdir(parents=True, exist_ok=True)

class Settings(BaseModel):
    PROJECT_NAME: str = "Automated PII Anonymization & Redaction Engine"
    VERSION: str = "1.0.0"
    COMPLIANCE_STANDARD: str = "DPDP Act 2023 (Digital Personal Data Protection)"
    
    # Confidence Score Thresholds
    STRUCTURED_PII_THRESHOLD: float = 0.80
    CONTEXTUAL_PII_THRESHOLD: float = 0.65
    
    # Visual Redaction Styling
    REDACTION_FILL_COLOR: tuple = (0.0, 0.0, 0.0)  # RGB Black
    REDACTION_TEXT_COLOR: tuple = (1.0, 1.0, 1.0)  # RGB White
    INCLUDE_LEGAL_WATERMARK: bool = False
    
    # Entity Visual Colors (RGB 0-255 for OpenCV/Streamlit overlays)
    ENTITY_COLORS: Dict[str, tuple] = {
        "IN_AADHAAR": (230, 57, 70),       # Crimson Red
        "IN_PAN": (244, 162, 97),          # Orange
        "IN_PHONE": (42, 157, 143),        # Teal Green
        "IN_VOTER_ID": (38, 70, 83),       # Deep Navy
        "IN_IFSC": (142, 68, 173),         # Purple
        "IN_BANK_ACCOUNT": (231, 76, 60),  # Coral Red
        "PERSON": (233, 196, 106),         # Warm Amber
        "GPE": (52, 152, 219),             # Cerulean Blue
        "LOC": (41, 128, 185),             # Slate Blue
        "ORG": (155, 89, 182),             # Lilac
        "EMAIL_ADDRESS": (26, 188, 156),   # Turquoise
        "DATE_TIME": (149, 165, 166),      # Gray
        "CUSTOM": (192, 57, 43)            # Dark Red
    }
    
    # Context keywords for score enhancement
    CONTEXT_WORDS: Dict[str, List[str]] = {
        "IN_AADHAAR": ["aadhaar", "uid", "uidai", "adhar", "unique identity", "12-digit"],
        "IN_PAN": ["pan", "pan card", "permanent account", "income tax", "pan no"],
        "IN_PHONE": ["mobile", "phone", "contact", "cell", "tel", "whatsapp", "ph no", "call"],
        "IN_VOTER_ID": ["voter", "epic", "election", "elector", "identity card", "chunav"],
        "IN_IFSC": ["ifsc", "ifsc code", "rtgs", "neft", "branch code", "bank branch"],
        "IN_BANK_ACCOUNT": ["account", "a/c", "bank account", "savings account", "current account", "sb a/c"],
        "PERSON": ["shri", "smt", "kumari", "mr", "mrs", "dr", "s/o", "d/o", "w/o", "c/o", "beneficiary", "applicant", "name"],
        "GPE": ["village", "gram", "tehsil", "taluk", "district", "zilla", "post", "pincode", "state", "pradesh", "mouza", "ward"]
    }

settings = Settings()
