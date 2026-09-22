"""
Synthetic Benchmark Generator for Indian Public Sector Documents.
Generates 100 realistic mock government circulars, beneficiary sheets,
land registry notices, and court orders with precise ground truth annotations.
"""
import os
import random
import json
from pathlib import Path
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from faker import Faker

# Add project root to sys.path
import sys
BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from backend.app.utils.verhoeff import generate_verhoeff

fake = Faker('en_IN')
random.seed(42)

BENCHMARK_DIR = BASE_DIR / "data" / "synthetic_benchmark"
BENCHMARK_DIR.mkdir(parents=True, exist_ok=True)
GROUND_TRUTH_FILE = BENCHMARK_DIR / "ground_truth.json"

INDIAN_DISTRICTS = [
    ("Lucknow", "Uttar Pradesh"), ("Varanasi", "Uttar Pradesh"), ("Kanpur", "Uttar Pradesh"),
    ("Prayagraj", "Uttar Pradesh"), ("Gorakhpur", "Uttar Pradesh"), ("Agra", "Uttar Pradesh"),
    ("Meerut", "Uttar Pradesh"), ("Ayodhya", "Uttar Pradesh"), ("Jhansi", "Uttar Pradesh")
]

TEHSILS = ["Sadar", "Mohanlalganj", "Bakshi Ka Talab", "Malihabad", "Koil", "Chandauli", "Gyanpur"]

def generate_valid_aadhaar() -> str:
    """Generates a 12-digit Aadhaar number with valid Verhoeff checksum."""
    first = str(random.randint(2, 9))
    middle = "".join(str(random.randint(0, 9)) for _ in range(10))
    first_11 = first + middle
    checksum = generate_verhoeff(first_11)
    full = first_11 + checksum
    return f"{full[:4]} {full[4:8]} {full[8:]}"

def generate_valid_pan() -> str:
    """Generates a valid Indian PAN format: 5 letters, 4 digits, 1 letter."""
    chars1 = "".join(random.choices("ABCDEFGHJKLMNPQRSTUVWXYZ", k=3))
    entity_char = random.choice(["P", "C", "H", "F", "A", "T", "B"])
    surname_char = random.choice("ABCDEFGHIJKLMNOPQRSTUVWXYZ")
    digits = f"{random.randint(1000, 9999)}"
    last_char = random.choice("ABCDEFGHIJKLMNOPQRSTUVWXYZ")
    return f"{chars1}{entity_char}{surname_char}{digits}{last_char}"

def generate_valid_ifsc() -> str:
    """Generates RBI-compliant IFSC code."""
    bank = random.choice(["SBIN", "PUNB", "BARB", "HDFC", "ICIC", "CNRB", "UBIN"])
    branch = "".join(random.choices("0123456789ABCDEFGHJKLMNPQRSTUVWXYZ", k=6))
    return f"{bank}0{branch}"

def generate_valid_epic() -> str:
    """Generates Indian Voter ID (EPIC)."""
    alpha = "".join(random.choices("ABCDEFGHIJKLMNOPQRSTUVWXYZ", k=3))
    num = f"{random.randint(1000000, 9999999)}"
    return f"{alpha}{num}"

def generate_mock_document(doc_id: int, doc_type: str) -> dict:
    filename = f"mock_doc_{doc_id:03d}_{doc_type}.pdf"
    pdf_path = BENCHMARK_DIR / filename

    doc = SimpleDocTemplate(str(pdf_path), pagesize=letter, leftMargin=40, rightMargin=40, topMargin=40, bottomMargin=40)
    styles = getSampleStyleSheet()
    story = []

    district, state = random.choice(INDIAN_DISTRICTS)
    tehsil = random.choice(TEHSILS)

    # Title & Header
    title_style = ParagraphStyle('TitleStyle', parent=styles['Heading1'], fontSize=14, leading=18, alignment=1, textColor=colors.navy)
    sub_style = ParagraphStyle('SubStyle', parent=styles['Normal'], fontSize=9, leading=12, alignment=1, textColor=colors.dimgray)
    body_style = ParagraphStyle('Body', parent=styles['Normal'], fontSize=9.5, leading=14)

    truth_entities = []

    if doc_type == "beneficiary_sheet":
        story.append(Paragraph("GOVERNMENT OF UTTAR PRADESH", title_style))
        story.append(Paragraph(f"DEPARTMENT OF RURAL DEVELOPMENT & PANCHAYATI RAJ<br/>DISTRICT: {district.upper()} | TEHSIL: {tehsil.upper()}", sub_style))
        story.append(Spacer(1, 12))
        story.append(Paragraph("<b>PUBLIC NOTICE: DIRECT BENEFIT DISBURSEMENT BENEFICIARY SHEET (2025-2026)</b>", ParagraphStyle('Notice', parent=body_style, alignment=1)))
        story.append(Paragraph("Notice is hereby given that the following registered beneficiaries have been sanctioned agricultural grant subsidies under the state welfare scheme. Any objections must be submitted within 15 days.", body_style))
        story.append(Spacer(1, 10))

        # Table data
        table_data = [["Sr", "Beneficiary Name", "Aadhaar UID", "Mobile", "Bank Account", "IFSC Code"]]
        
        for r in range(1, 5):
            name = fake.name_male()
            aadhaar = generate_valid_aadhaar()
            mobile = f"+91 {random.randint(6, 9)}{random.randint(100000000, 999999999)}"
            account = str(random.randint(10000000000, 99999999999))
            ifsc = generate_valid_ifsc()

            table_data.append([str(r), name, aadhaar, mobile, account, ifsc])

            truth_entities.append({"entity_type": "PERSON", "text": name})
            truth_entities.append({"entity_type": "IN_AADHAAR", "text": aadhaar})
            truth_entities.append({"entity_type": "IN_PHONE", "text": mobile})
            truth_entities.append({"entity_type": "IN_BANK_ACCOUNT", "text": account})
            truth_entities.append({"entity_type": "IN_IFSC", "text": ifsc})

        t = Table(table_data, colWidths=[25, 120, 110, 95, 95, 85])
        t.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#2c3e50')),
            ('TEXTCOLOR', (0,0), (-1,0), colors.white),
            ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
            ('FONTSIZE', (0,0), (-1,0), 8.5),
            ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
            ('ALIGN', (0,0), (-1,-1), 'CENTER'),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ]))
        story.append(t)
        story.append(Spacer(1, 15))
        story.append(Paragraph(f"Authorized Signatory: Block Development Officer, Tehsil {tehsil}, {district}, {state}.", body_style))
        truth_entities.append({"entity_type": "GPE", "text": district})
        truth_entities.append({"entity_type": "GPE", "text": tehsil})

    elif doc_type == "land_registry":
        story.append(Paragraph("OFFICE OF THE SUB-REGISTRAR & TEHSILDAR", title_style))
        story.append(Paragraph(f"REVENUE DEPARTMENT, TEHSIL: {tehsil.upper()}, DISTRICT: {district.upper()}", sub_style))
        story.append(Spacer(1, 12))
        story.append(Paragraph("<b>LAND RECORD MUTATION ORDER & PROCEEDINGS (KHASRA-KHATAUNI)</b>", ParagraphStyle('Notice', parent=body_style, alignment=1)))
        story.append(Spacer(1, 10))

        owner = fake.name_male()
        father = fake.name_male()
        pan = generate_valid_pan()
        mobile = f"+91 {random.randint(6, 9)}{random.randint(100000000, 999999999)}"
        aadhaar = generate_valid_aadhaar()

        text = (
            f"Case No: REV/{random.randint(1000, 9999)}/2026. In the matter of agricultural land parcel situated at "
            f"Village {fake.first_name()} Puram, Tehsil {tehsil}, District {district}. "
            f"The registered tenure holder Shri {owner}, S/o Shri {father}, permanent resident of {district}, "
            f"bearing PAN {pan}, Aadhaar No. {aadhaar}, and registered phone {mobile}, has submitted an application for "
            f"mutation of title deed under Section 34 of the UP Revenue Code. Notice is hereby issued to all concerned."
        )
        story.append(Paragraph(text, body_style))
        story.append(Spacer(1, 15))
        story.append(Paragraph("Issued under the seal of the Tehsildar & Executive Magistrate.", body_style))

        truth_entities.append({"entity_type": "PERSON", "text": owner})
        truth_entities.append({"entity_type": "PERSON", "text": father})
        truth_entities.append({"entity_type": "IN_PAN", "text": pan})
        truth_entities.append({"entity_type": "IN_AADHAAR", "text": aadhaar})
        truth_entities.append({"entity_type": "IN_PHONE", "text": mobile})
        truth_entities.append({"entity_type": "GPE", "text": district})
        truth_entities.append({"entity_type": "GPE", "text": tehsil})

    elif doc_type == "municipal_notice":
        story.append(Paragraph(f"NAGAR NIGAM / MUNICIPAL CORPORATION, {district.upper()}", title_style))
        story.append(Spacer(1, 10))
        story.append(Paragraph("<b>TENDER ALLOTMENT & CONTRACTOR DISCLOSURE NOTICE</b>", ParagraphStyle('Notice', parent=body_style, alignment=1)))
        story.append(Spacer(1, 10))

        contractor = fake.name()
        pan = generate_valid_pan()
        epic = generate_valid_epic()
        phone = f"0{random.randint(6, 9)}{random.randint(100000000, 999999999)}"
        email = fake.email()

        text = (
            f"This public circular notifies that the tender for civic maintenance in Zone {random.randint(1, 8)} "
            f"has been awarded to Shri {contractor}. The contractor's official tax identity is PAN {pan}, "
            f"Voter ID / EPIC {epic}, contact telephone {phone}, and correspondence email {email}. "
            f"Registered correspondence address: Sector {random.randint(1, 24)}, Civil Lines, {district}."
        )
        story.append(Paragraph(text, body_style))
        truth_entities.append({"entity_type": "PERSON", "text": contractor})
        truth_entities.append({"entity_type": "IN_PAN", "text": pan})
        truth_entities.append({"entity_type": "IN_VOTER_ID", "text": epic})
        truth_entities.append({"entity_type": "IN_PHONE", "text": phone})
        truth_entities.append({"entity_type": "EMAIL_ADDRESS", "text": email})
        truth_entities.append({"entity_type": "GPE", "text": district})

    else:  # court_order
        story.append(Paragraph(f"IN THE COURT OF DISTRICT & SESSIONS JUDGE, {district.upper()}", title_style))
        story.append(Spacer(1, 10))
        story.append(Paragraph("<b>PUBLIC CITATION NOTICE IN CIVIL PROCEEDING</b>", ParagraphStyle('Notice', parent=body_style, alignment=1)))
        story.append(Spacer(1, 10))

        litigant = fake.name()
        voter = generate_valid_epic()
        aadhaar = generate_valid_aadhaar()
        mobile = f"+91 {random.randint(6, 9)}{random.randint(100000000, 999999999)}"

        text = (
            f"Civil Suit No. {random.randint(100, 999)} of 2026. Whereas summons have been issued to the respondent "
            f"Smt/Shri {litigant}, resident of Tehsil {tehsil}, {district}, holding Voter ID {voter} and "
            f"Aadhaar Number {aadhaar}. Primary phone on court records: {mobile}. "
            f"Take notice that in default of appearance on the appointed date, the matter shall be decided ex-parte."
        )
        story.append(Paragraph(text, body_style))
        truth_entities.append({"entity_type": "PERSON", "text": litigant})
        truth_entities.append({"entity_type": "IN_VOTER_ID", "text": voter})
        truth_entities.append({"entity_type": "IN_AADHAAR", "text": aadhaar})
        truth_entities.append({"entity_type": "IN_PHONE", "text": mobile})
        truth_entities.append({"entity_type": "GPE", "text": district})
        truth_entities.append({"entity_type": "GPE", "text": tehsil})

    doc.build(story)

    return {
        "doc_id": doc_id,
        "filename": filename,
        "doc_type": doc_type,
        "truth_entities": truth_entities
    }

def main():
    print("Generating 100 synthetic Indian government benchmark documents...")
    doc_types = [
        ("beneficiary_sheet", 30),
        ("land_registry", 30),
        ("municipal_notice", 20),
        ("court_order", 20)
    ]

    all_metadata = []
    doc_counter = 1

    for dtype, count in doc_types:
        for _ in range(count):
            meta = generate_mock_document(doc_counter, dtype)
            all_metadata.append(meta)
            doc_counter += 1

    with open(GROUND_TRUTH_FILE, "w", encoding="utf-8") as f:
        json.dump(all_metadata, f, indent=2)

    print(f"Successfully generated 100 benchmark documents at {BENCHMARK_DIR}")
    print(f"Ground truth saved to {GROUND_TRUTH_FILE}")

if __name__ == "__main__":
    main()
