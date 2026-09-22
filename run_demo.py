"""
End-to-End Demo Runner for the Automated PII Anonymization & Redaction Engine.
Demonstrates:
1. Ingestion of a citizen administrative document
2. Hybrid PII detection (Aadhaar with Verhoeff D5, PAN, Phone, Names)
3. Irreversible binary stream redaction
4. Deep metadata scrubbing
5. Tamper-evident Zero-Plaintext Audit JSON generation
"""
import sys
import json
from pathlib import Path

# Set up project root in path
BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from backend.app.core.pipeline import RedactionPipeline

def run_demo():
    print("=" * 75)
    print("  AUTOMATED PII ANONYMIZATION & REDACTION ENGINE (DPDP ACT 2023 COMPLIANT)")
    print("=" * 75)

    pdf_candidates = list((BASE_DIR / "data" / "synthetic_benchmark").glob("mock_doc_*.pdf"))
    if not pdf_candidates:
        print("[!] No benchmark PDF found in data/synthetic_benchmark/")
        return
    sample_pdf = pdf_candidates[0]

    print(f"[*] Processing Target Document: {sample_pdf.name}")
    pipeline = RedactionPipeline()

    result = pipeline.process_document(
        file_path=sample_pdf,
        confidence_threshold=0.70
    )

    print("\n[+] PROCESSING COMPLETE:")
    print(f"    - Original File:       {result['original_file']}")
    print(f"    - Total Pages:         {result['page_count']}")
    print(f"    - Redactions Applied:  {result['total_redactions']}")
    print(f"    - Elapsed Time:        {result['elapsed_seconds']:.3f} seconds")
    print(f"    - Sanitized Output:    {result['sanitized_file']}")
    print(f"    - Audit Log:           {result['audit_file']}")

    audit_path = Path(result["audit_file"])
    if audit_path.exists():
        with open(audit_path, "r", encoding="utf-8") as f:
            audit_data = json.load(f)
        
        print("\n" + "-" * 75)
        print("  TAMPER-EVIDENT AUDIT MANIFEST (ZERO-PLAINTEXT VERIFIED)")
        print("-" * 75)
        print(f"  Audit ID:             {audit_data.get('audit_id')}")
        print(f"  Compliance Standard:  {audit_data.get('compliance_standard')}")
        print(f"  Original SHA-256:     {audit_data['file_manifest']['original_sha256']}")
        print(f"  Sanitized SHA-256:    {audit_data['file_manifest']['sanitized_sha256']}")
        print(f"  Zero Plaintext Cert:  {audit_data.get('zero_plaintext_pii_certification')}")
        print("\n  Redacted Entities Breakdown:")
        for ent, cnt in audit_data["redaction_summary"]["entity_type_counts"].items():
            print(f"    - {ent:<18}: {cnt} instances")
        print("=" * 75)

if __name__ == "__main__":
    run_demo()
