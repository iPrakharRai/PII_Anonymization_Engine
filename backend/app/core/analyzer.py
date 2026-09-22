"""
Hybrid Identification Engine.
Combines Microsoft Presidio AnalyzerEngine, custom Indian deterministic recognizers,
and spaCy statistical Named Entity Recognition with Indian administrative context weighting.
"""
from typing import List, Dict, Any, Optional
import re
import spacy
from presidio_analyzer import AnalyzerEngine, RecognizerRegistry
from presidio_analyzer.nlp_engine import SpacyNlpEngine, NlpEngineProvider
from backend.app.core.recognizers import (
    IndianAadhaarRecognizer,
    IndianPANRecognizer,
    IndianPhoneRecognizer,
    IndianVoterIDRecognizer,
    IndianIFSCRecognizer,
    IndianBankAccountRecognizer,
    IndianPersonRecognizer
)
from backend.app.config import settings

class PIIAnalyzer:
    """
    Hybrid Analyzer orchestrating:
    1. Deterministic Rule & Checksum Layer (Aadhaar, PAN, Phone, Voter ID, IFSC, Account)
    2. Statistical Transformer / spaCy NER Layer (PERSON, GPE, LOC, ORG)
    3. Indian Contextual Score Booster (kinship prefixes, administrative tokens)
    """
    def __init__(self):
        # 1. Configure spaCy NLP Engine
        nlp_configuration = {
            "nlp_engine_name": "spacy",
            "models": [{"lang_code": "en", "model_name": "en_core_web_sm"}],
        }
        provider = NlpEngineProvider(nlp_configuration=nlp_configuration)
        nlp_engine = provider.create_engine()

        # 2. Setup Recognizer Registry
        registry = RecognizerRegistry()
        registry.load_predefined_recognizers(nlp_engine=nlp_engine)

        # 3. Add Custom Indian Recognizers
        registry.add_recognizer(IndianAadhaarRecognizer())
        registry.add_recognizer(IndianPANRecognizer())
        registry.add_recognizer(IndianPhoneRecognizer())
        registry.add_recognizer(IndianVoterIDRecognizer())
        registry.add_recognizer(IndianIFSCRecognizer())
        registry.add_recognizer(IndianBankAccountRecognizer())
        registry.add_recognizer(IndianPersonRecognizer())

        # 4. Initialize Presidio Engine
        self.analyzer = AnalyzerEngine(
            nlp_engine=nlp_engine,
            registry=registry,
            supported_languages=["en"]
        )
        self.nlp = spacy.load("en_core_web_sm")

    def boost_contextual_scores(self, text: str, entities: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Applies domain-specific contextual boosting for Indian administrative documents.
        E.g. kinship markers 'S/o', 'W/o', 'Shri' boost PERSON entities.
        'Village', 'Tehsil', 'District' boost GPE/LOC entities.
        """
        boosted = []
        for ent in entities:
            start, end = ent["start"], ent["end"]
            ent_type = ent["entity_type"]
            score = ent["score"]
            
            # Context window around the entity
            left_window = text[max(0, start - 40):start].lower()
            right_window = text[end:min(len(text), end + 40)].lower()
            context_window = left_window + " " + right_window

            if ent_type == "PERSON":
                kinship_markers = ["s/o", "d/o", "w/o", "c/o", "shri", "smt", "shrimati", "kumari", "son of", "wife of", "beneficiary:", "name:"]
                if any(m in left_window for m in kinship_markers):
                    score = min(0.98, score + 0.25)
            elif ent_type in ["GPE", "LOC"]:
                admin_markers = ["village", "gram", "tehsil", "taluk", "dist", "district", "zilla", "post", "pin", "pincode", "pradesh"]
                if any(m in context_window for m in admin_markers):
                    score = min(0.96, score + 0.20)
            elif ent_type in ["IN_AADHAAR", "IN_PAN", "IN_IFSC", "IN_BANK_ACCOUNT"]:
                context_keys = settings.CONTEXT_WORDS.get(ent_type, [])
                if any(k in context_window for k in context_keys):
                    score = min(1.0, score + 0.15)

            ent["score"] = round(score, 3)
            boosted.append(ent)
        return boosted

    def analyze_text(self, text: str, language: str = "en") -> List[Dict[str, Any]]:
        """
        Executes hybrid identification across both deterministic & statistical layers.
        Returns deduplicated, non-overlapping entity spans sorted by position.
        """
        if not text or not text.strip():
            return []

        # Presidio detection
        presidio_results = self.analyzer.analyze(
            text=text,
            language=language,
            entities=[
                "IN_AADHAAR", "IN_PAN", "IN_PHONE", "IN_VOTER_ID",
                "IN_IFSC", "IN_BANK_ACCOUNT", "PERSON", "GPE",
                "LOC", "ORG", "EMAIL_ADDRESS"
            ]
        )

        # Administrative institution and document title words to avoid tagging as citizen PERSON
        ADMIN_TERMS = {
            "government", "uttar", "pradesh", "department", "rural", "development",
            "panchayati", "raj", "public", "notice", "sub-registrar", "tehsildar",
            "revenue", "municipal", "corporation", "nigam", "executive",
            "magistrate", "sessions", "judge", "court", "district", "authorized",
            "signatory", "block", "officer", "zone", "sector", "civil", "lines",
            "khasra", "khatauni", "khasra-khatauni", "mutation", "order", "proceedings", "case", "suit",
            "tender", "allotment", "contractor", "disclosure", "beneficiary", "sheet"
        }
        KNOWN_GPE = {"uttar pradesh", "lucknow", "varanasi", "kanpur", "prayagraj", "gorakhpur", "agra", "meerut", "ayodhya", "jhansi", "sadar", "mohanlalganj", "bakshi", "malihabad", "koil", "chandauli", "gyanpur"}

        detected = []
        for r in presidio_results:
            span_text = text[r.start:r.end].strip()
            if not span_text:
                continue

            ent_type = r.entity_type
            words_lower = set(re.findall(r"\w+", span_text.lower()))

            if ent_type == "PERSON":
                if any(c.isdigit() for c in span_text):
                    sub_names = list(re.finditer(r"\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)+\b", span_text))
                    for sn in sub_names:
                        sn_text = sn.group().strip()
                        sn_words = set(re.findall(r"\w+", sn_text.lower()))
                        if not (sn_words & ADMIN_TERMS) and not any(k in sn_text.lower() for k in KNOWN_GPE):
                            detected.append({
                                "start": r.start + sn.start(),
                                "end": r.start + sn.end(),
                                "entity_type": "PERSON",
                                "score": 0.88,
                                "text": sn_text
                            })
                    continue
                if (words_lower & ADMIN_TERMS) or any(k in span_text.lower() for k in KNOWN_GPE):
                    if any(k in span_text.lower() for k in KNOWN_GPE) or "tehsil" in span_text.lower() or "district" in span_text.lower():
                        ent_type = "GPE"
                    else:
                        continue
            elif ent_type in ["LOC", "GPE"]:
                ent_type = "GPE"

            detected.append({
                "start": r.start,
                "end": r.end,
                "entity_type": ent_type,
                "score": r.score,
                "text": span_text
            })

        # spaCy fallback / supplement for Indian administrative named entities
        doc = self.nlp(text)
        for ent in doc.ents:
            if ent.label_ in ["PERSON", "GPE", "LOC", "ORG"]:
                ent_clean = ent.text.strip()
                words_lower = set(re.findall(r"\w+", ent_clean.lower()))

                ent_label = ent.label_
                if ent.label_ == "PERSON":
                    if any(c.isdigit() for c in ent_clean):
                        continue
                    if (words_lower & ADMIN_TERMS) or any(k in ent_clean.lower() for k in KNOWN_GPE):
                        if any(k in ent_clean.lower() for k in KNOWN_GPE) or "tehsil" in ent_clean.lower() or "district" in ent_clean.lower():
                            ent_label = "GPE"
                        else:
                            continue
                elif ent.label_ in ["LOC", "GPE"]:
                    ent_label = "GPE"

                # Check if already covered
                overlap = any(
                    max(d["start"], ent.start_char) < min(d["end"], ent.end_char)
                    for d in detected
                )
                if not overlap and len(ent_clean) > 1:
                    detected.append({
                        "start": ent.start_char,
                        "end": ent.end_char,
                        "entity_type": ent_label,
                        "score": 0.80 if ent_label == "GPE" else 0.75,
                        "text": ent_clean
                    })

        # Administrative Header GPE Pattern: DISTRICT: <District> | TEHSIL: <Tehsil>
        admin_header_matches = re.finditer(r"\b(?:DISTRICT|TEHSIL|VILLAGE|MOUZA)[:\s]+([A-Za-z\s]+?)(?=\s*[\|\,\n\.]|\s{2,}|$)", text, re.IGNORECASE)
        for m in admin_header_matches:
            gpe_text = m.group(1).strip()
            if len(gpe_text) > 2:
                overlap = any(max(d["start"], m.start(1)) < min(d["end"], m.end(1)) for d in detected)
                if not overlap:
                    detected.append({
                        "start": m.start(1),
                        "end": m.end(1),
                        "entity_type": "GPE",
                        "score": 0.95,
                        "text": gpe_text
                    })

        # Village pattern: Village <Name>
        village_matches = re.finditer(r"\bVillage\s+([A-Za-z\s]+?)(?=[,\.\n]|\s+Tehsil|\s+District|$)", text, re.IGNORECASE)
        for m in village_matches:
            v_text = m.group(1).strip()
            if len(v_text) > 2:
                overlap = any(max(d["start"], m.start(1)) < min(d["end"], m.end(1)) for d in detected)
                if not overlap:
                    detected.append({
                        "start": m.start(1),
                        "end": m.end(1),
                        "entity_type": "GPE",
                        "score": 0.95,
                        "text": v_text
                    })

        # Exact Known Districts / Cities in text (sorted by descending length)
        for gpe in sorted(KNOWN_GPE, key=len, reverse=True):
            for m in re.finditer(rf"\b{re.escape(gpe)}\b", text, re.IGNORECASE):
                span_text = m.group().strip()
                overlap = any(max(d["start"], m.start()) < min(d["end"], m.end()) for d in detected)
                if not overlap:
                    detected.append({
                        "start": m.start(),
                        "end": m.end(),
                        "entity_type": "GPE",
                        "score": 0.96,
                        "text": span_text
                    })

        # Apply contextual boost
        boosted = self.boost_contextual_scores(text, detected)

        # Deduplicate & resolve overlapping spans (structured IDs take priority over generic entities)
        STRUCTURED_PRIORITY = {"IN_AADHAAR", "IN_PAN", "IN_IFSC", "IN_PHONE", "IN_BANK_ACCOUNT", "IN_VOTER_ID", "EMAIL_ADDRESS"}
        boosted.sort(key=lambda x: (x["start"], -x["score"]))
        resolved = []
        for curr in boosted:
            if not resolved:
                resolved.append(curr)
                continue
            prev = resolved[-1]
            if curr["start"] < prev["end"]:
                # Overlap detected
                if curr["entity_type"] in STRUCTURED_PRIORITY and prev["entity_type"] not in STRUCTURED_PRIORITY:
                    resolved[-1] = curr
                elif prev["entity_type"] in STRUCTURED_PRIORITY and curr["entity_type"] not in STRUCTURED_PRIORITY:
                    pass  # keep prev structured ID
                elif (curr["end"] - curr["start"]) > (prev["end"] - prev["start"]):
                    resolved[-1] = curr
                elif curr["score"] > prev["score"]:
                    resolved[-1] = curr
            else:
                resolved.append(curr)

        return resolved
