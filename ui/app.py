"""
Operator Review Portal - Streamlit Frontend.
Enables public administration clerks to inspect flagged bounding boxes,
toggle false positives, perform forensic redactions, and export DPDP-compliant audit logs.
"""
import streamlit as st
import fitz  # PyMuPDF
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import io
import json
import time
from pathlib import Path
import sys

# Ensure project root is in sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from backend.app.config import settings, INPUT_DIR, OUTPUT_DIR, AUDIT_DIR
from backend.app.core.pipeline import RedactionPipeline
from backend.app.core.ingestion import DocumentIngestionEngine
from backend.app.core.sanitization import SanitizationEngine
from backend.app.core.audit import AuditLogger

# Page Configuration
st.set_page_config(
    page_title="DPDP Document Sanitizer | Operator Portal",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom Styling for Enhanced Readability & Accessibility
st.markdown("""
<style>
    /* Global Base Font & Line Height Scaling */
    html, body, [class*="css"], .stMarkdown, p, div, span, label {
        font-size: 1.15rem !important;
        line-height: 1.65 !important;
    }

    /* Main Title & Subtitle */
    .main-header {
        font-size: 2.8rem !important;
        font-weight: 800 !important;
        color: #1e3a8a !important;
        margin-bottom: 0.4rem !important;
        line-height: 1.25 !important;
        letter-spacing: -0.5px;
    }
    .sub-header {
        font-size: 1.35rem !important;
        color: #374151 !important;
        margin-bottom: 1.8rem !important;
        font-weight: 500 !important;
        line-height: 1.4 !important;
    }

    /* Section Headings */
    h1, [data-testid="stHeadingWithActionElements"] h1 {
        font-size: 2.3rem !important;
        font-weight: 800 !important;
    }
    h2, [data-testid="stHeadingWithActionElements"] h2 {
        font-size: 1.85rem !important;
        font-weight: 700 !important;
    }
    h3, [data-testid="stHeadingWithActionElements"] h3 {
        font-size: 1.45rem !important;
        font-weight: 650 !important;
    }

    /* Status & Compliance Badges */
    .badge-pill {
        display: inline-block;
        padding: 0.35rem 0.85rem;
        border-radius: 9999px;
        font-size: 1.0rem !important;
        font-weight: 650 !important;
        margin-right: 0.5rem;
        margin-bottom: 0.3rem;
    }
    .badge-compliance { background-color: #d1fae5; color: #065f46; border: 1.5px solid #6ee7b7; }
    .badge-digital { background-color: #dbeafe; color: #1e40af; border: 1.5px solid #93c5fd; }
    .badge-scanned { background-color: #fef3c7; color: #92400e; border: 1.5px solid #fcd34d; }

    /* Action Buttons */
    .stButton > button {
        font-size: 1.25rem !important;
        font-weight: 700 !important;
        padding: 0.7rem 1.6rem !important;
        border-radius: 10px !important;
        box-shadow: 0 2px 4px rgba(0,0,0,0.08);
    }

    /* Download Buttons */
    .stDownloadButton > button {
        font-size: 1.2rem !important;
        font-weight: 700 !important;
        padding: 0.65rem 1.4rem !important;
        border-radius: 10px !important;
    }

    /* Sidebar Labels & Controls */
    [data-testid="stSidebar"] p, 
    [data-testid="stSidebar"] label,
    [data-testid="stSidebar"] div {
        font-size: 1.15rem !important;
    }
    [data-testid="stSidebar"] h1 {
        font-size: 1.9rem !important;
    }

    /* Form Controls: Inputs, Selectors, Sliders & Checkboxes */
    .stSelectbox label, .stSlider label, .stMultiSelect label, .stCheckbox label, .stFileUploader label {
        font-size: 1.25rem !important;
        font-weight: 650 !important;
        color: #1f2937 !important;
    }

    /* Entity Table & Text Spans */
    code {
        font-size: 1.1rem !important;
        padding: 0.2rem 0.4rem !important;
    }
    .stCaption, [data-testid="stCaptionContainer"] p {
        font-size: 1.05rem !important;
        color: #4b5563 !important;
    }

    /* Alerts & Banners */
    .stAlert p {
        font-size: 1.15rem !important;
    }
</style>
""", unsafe_allow_html=True)

# Cache Pipeline Instance
@st.cache_resource
def get_pipeline():
    return RedactionPipeline()

pipeline = get_pipeline()

# Sidebar Controls
st.sidebar.image("https://img.icons8.com/color/96/000000/shield.png", width=64)
st.sidebar.title("Configuration")
st.sidebar.markdown("""
<div style="margin-bottom: 1rem;">
    <span class="badge-pill badge-compliance">DPDP Act 2023</span>
    <span class="badge-pill badge-digital">CSTUP Blueprint</span>
</div>
""", unsafe_allow_html=True)

conf_threshold = st.sidebar.slider(
    "Confidence Threshold",
    min_value=0.40,
    max_value=0.95,
    value=0.65,
    step=0.05,
    help="Detections below this score are filtered out by default."
)

active_entities = st.sidebar.multiselect(
    "Entity Filters",
    options=[
        "IN_AADHAAR", "IN_PAN", "IN_PHONE", "IN_VOTER_ID",
        "IN_IFSC", "IN_BANK_ACCOUNT", "PERSON", "GPE", "LOC", "ORG"
    ],
    default=[
        "IN_AADHAAR", "IN_PAN", "IN_PHONE", "IN_VOTER_ID",
        "IN_IFSC", "IN_BANK_ACCOUNT", "PERSON", "GPE"
    ],
    help="Select which PII types should be targeted for redaction."
)

redaction_mode = st.sidebar.radio(
    "Sanitization Mode",
    options=["Forensic Binary Destruction (True Stream)", "High-Contrast Visual Blackout"],
    index=0
)

# Header
st.markdown('<div class="main-header">Automated PII Anonymization & Redaction Engine</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="sub-header">Public Sector Document Sanitizer | Indian National ID Checksums (Verhoeff & Luhn) | DPDP Act 2023 Zero-Leak Verification</div>',
    unsafe_allow_html=True
)

# File Uploader
uploaded_file = st.file_uploader(
    "Drag & drop public circular, welfare sheet, land registry notice, or court order (PDF/Image)",
    type=["pdf", "png", "jpg", "jpeg"]
)

def render_page_with_bboxes(page: fitz.Page, entities: list, dpi: int = 150) -> Image.Image:
    """Renders PDF page to image and draws bounding box overlays with tags."""
    pix = page.get_pixmap(dpi=dpi)
    img = Image.open(io.BytesIO(pix.tobytes("png"))).convert("RGBA")
    overlay = Image.new("RGBA", img.size, (255, 255, 255, 0))
    draw = ImageDraw.Draw(overlay)

    scale = dpi / 72.0

    for ent in entities:
        if not ent.get("is_approved", True):
            continue
        bbox = ent["bbox"]
        ent_type = ent.get("entity_type", "PII")
        color = settings.ENTITY_COLORS.get(ent_type, (220, 53, 69))
        fill_color = (*color, 75)
        border_color = (*color, 230)

        x0, y0, x1, y1 = [coord * scale for coord in bbox]
        draw.rectangle([x0, y0, x1, y1], fill=fill_color, outline=border_color, width=3)
        tag_text = f" {ent_type} "
        tag_w = len(tag_text) * 8.5
        draw.rectangle([x0, max(0, y0 - 18), x0 + tag_w, max(0, y0)], fill=border_color)
        draw.text((x0 + 2, max(0, y0 - 16)), tag_text, fill=(255, 255, 255, 255))

    return Image.alpha_composite(img, overlay)

if uploaded_file is not None:
    # Save uploaded file
    input_path = INPUT_DIR / uploaded_file.name
    with open(input_path, "wb") as f:
        f.write(uploaded_file.getbuffer())

    # Open document
    doc = fitz.open(str(input_path))
    total_pages = len(doc)

    st.success(f"Successfully loaded '{uploaded_file.name}' ({total_pages} page{'s' if total_pages > 1 else ''})")

    # Process Analysis Session State
    session_key = f"analysis_{uploaded_file.name}_{conf_threshold}"
    if session_key not in st.session_state:
        with st.spinner("Analyzing document structure & detecting PII entities..."):
            pages_data = []
            for page_idx in range(total_pages):
                page = doc[page_idx]
                ingest_res = DocumentIngestionEngine.ingest_page(page)
                raw_entities = pipeline.analyzer.analyze_text(ingest_res["full_text"])

                filtered = [
                    e for e in raw_entities
                    if e["score"] >= conf_threshold and e["entity_type"] in active_entities
                ]
                aligned = pipeline.align_entities_to_bboxes(filtered, ingest_res["tokens"])

                # Add review toggle state
                for item in aligned:
                    item["is_approved"] = True

                pages_data.append({
                    "page_idx": page_idx,
                    "ingest": ingest_res,
                    "entities": aligned
                })
            st.session_state[session_key] = pages_data

    pages_data = st.session_state[session_key]

    # Page Selector
    col_sel1, col_sel2 = st.columns([1, 3])
    with col_sel1:
        current_page_idx = st.selectbox(
            "Select Page for Review",
            options=range(total_pages),
            format_func=lambda x: f"Page {x + 1} of {total_pages}"
        )

    current_page_data = pages_data[current_page_idx]
    page = doc[current_page_idx]
    is_digital = current_page_data["ingest"]["is_digital"]
    engine_name = current_page_data["ingest"]["engine"]
    page_entities = current_page_data["entities"]

    with col_sel2:
        badge_html = f"""
        <div style="padding-top: 1.8rem;">
            <span class="badge-pill {'badge-digital' if is_digital else 'badge-scanned'}">
                {'Born-Digital (Native PyMuPDF Stream)' if is_digital else 'Scanned Document (OpenCV + EasyOCR)'}
            </span>
            <span class="badge-pill" style="background-color: #f3f4f6; color: #374151;">
                {len(page_entities)} Flagged Entities on this page
            </span>
        </div>
        """
        st.markdown(badge_html, unsafe_allow_html=True)

    # Side-by-Side Review Section
    col_left, col_right = st.columns(2)

    with col_left:
        st.subheader("1. Flagged Entity Overlay")
        annotated_img = render_page_with_bboxes(page, page_entities, dpi=130)
        st.image(annotated_img, use_container_width=True, caption=f"Original Page {current_page_idx + 1} with Flagged PII Bounding Boxes")

    with col_right:
        st.subheader("2. Operator Approval & Toggles")
        st.markdown("*Government clerks can review each detected token, verify checksums, and uncheck false positives prior to permanent binary erasure.*")

        if not page_entities:
            st.info("No PII detected on this page meeting the current threshold.")
        else:
            for idx, ent in enumerate(page_entities):
                c1, c2, c3, c4 = st.columns([1, 3, 2, 2])
                with c1:
                    is_checked = st.checkbox(
                        "Redact",
                        value=ent.get("is_approved", True),
                        key=f"p{current_page_idx}_e{idx}",
                        label_visibility="collapsed"
                    )
                    ent["is_approved"] = is_checked
                with c2:
                    st.markdown(f"**`{ent['entity_type']}`**")
                    st.caption(f"\"{ent.get('text', '')}\"")
                with c3:
                    st.markdown(f"Conf: **{ent['score']:.2f}**")
                with c4:
                    coords = [round(c, 1) for c in ent['bbox']]
                    st.caption(f"Box: {coords}")

    # Redaction Execution Button
    st.divider()
    if st.button("Apply Irreversible Redaction & Generate DPDP Audit Log", type="primary", use_container_width=True):
        with st.spinner("Forensically erasing binary streams and generating cryptographic audit log..."):
            # Prepare overrides map
            overrides = {}
            for p_info in pages_data:
                p_idx = p_info["page_idx"]
                approved_items = [e for e in p_info["entities"] if e.get("is_approved", True)]
                overrides[p_idx] = approved_items

            # Run pipeline
            pipeline_result = pipeline.process_document(
                file_path=input_path,
                confidence_threshold=conf_threshold,
                manual_overrides=overrides
            )

            st.success(
                f"Document successfully sanitized! Erased {pipeline_result['total_redactions']} PII entities in {pipeline_result['elapsed_seconds']}s."
            )

            # Download Buttons
            sanitized_pdf_path = Path(pipeline_result["sanitized_file"])
            audit_json_path = Path(pipeline_result["audit_file"])

            down_col1, down_col2 = st.columns(2)
            with down_col1:
                with open(sanitized_pdf_path, "rb") as f_pdf:
                    st.download_button(
                        label="⬇️ Download Sanitized PDF (DPDP Compliant)",
                        data=f_pdf.read(),
                        file_name=sanitized_pdf_path.name,
                        mime="application/pdf",
                        use_container_width=True
                    )

            with down_col2:
                with open(audit_json_path, "r", encoding="utf-8") as f_json:
                    st.download_button(
                        label="⬇️ Download Cryptographic Audit Log (JSON)",
                        data=f_json.read(),
                        file_name=audit_json_path.name,
                        mime="application/json",
                        use_container_width=True
                    )

            # Audit summary preview
            with st.expander("View Tamper-Evident Audit Log Details"):
                with open(audit_json_path, "r", encoding="utf-8") as f_json:
                    st.json(json.load(f_json))

    doc.close()
else:
    st.info("Upload a document above to begin automated PII detection and redaction.")
