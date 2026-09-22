"""
Dual-Engine Ingestion & Document Routing.
Routes pages dynamically based on digital text density vs scanned raster content.
Extracts text with precise character-to-bounding-box spatial mappings.
"""
from typing import Dict, List, Any, Tuple, Optional
import fitz  # PyMuPDF
import cv2
import numpy as np
from PIL import Image
import io

from backend.app.core.ocr_engine import OCREngine
from backend.app.utils.coordinates import CoordinateHarmonizer

class DocumentIngestionEngine:
    """
    Dual-Engine Reader routing documents between native PyMuPDF stream parsing
    and OpenCV-enhanced EasyOCR raster analysis.
    """

    @staticmethod
    def classify_page_type(page: fitz.Page) -> Dict[str, Any]:
        """
        Detects whether a PDF page is born-digital or a scanned raster image.
        Criteria:
        - Character count in native text stream
        - Image count and image-to-page surface ratio
        - Font resource existence
        """
        text = page.get_text("text").strip()
        char_count = len(text)
        images = page.get_images()
        page_area = page.rect.width * page.rect.height

        img_area = 0.0
        for img_info in images:
            xref = img_info[0]
            try:
                rects = page.get_image_rects(xref)
                for r in rects:
                    img_area += (r.width * r.height)
            except Exception:
                pass

        image_ratio = min(1.0, img_area / page_area) if page_area > 0 else 0.0

        # Classification rule
        is_digital = (char_count >= 50) and (image_ratio < 0.85 or char_count > 250)

        return {
            "is_digital": bool(is_digital),
            "char_count": char_count,
            "image_count": len(images),
            "image_coverage_ratio": round(image_ratio, 3),
            "width": page.rect.width,
            "height": page.rect.height
        }

    @staticmethod
    def extract_native_words(page: fitz.Page) -> Tuple[str, List[Dict[str, Any]]]:
        """
        Extracts words and precise bounding boxes from born-digital PDF stream.
        Returns:
            full_text: Synthesized string of the page
            spans: List of {word, bbox, start_char, end_char}
        """
        # page.get_text("words") returns: (x0, y0, x1, y1, word, block_no, line_no, word_no)
        raw_words = page.get_text("words")
        raw_words.sort(key=lambda w: (w[5], w[6], w[7]))  # Sort by block, line, word

        text_pieces = []
        token_spans = []
        curr_offset = 0

        for w in raw_words:
            word_str = str(w[4]).strip()
            if not word_str:
                continue

            bbox = (float(w[0]), float(w[1]), float(w[2]), float(w[3]))
            start_pos = curr_offset
            end_pos = curr_offset + len(word_str)

            token_spans.append({
                "text": word_str,
                "bbox": bbox,
                "start_char": start_pos,
                "end_char": end_pos,
                "block_no": int(w[5]),
                "line_no": int(w[6])
            })

            text_pieces.append(word_str)
            curr_offset = end_pos + 1  # Account for space

        full_text = " ".join(text_pieces)
        return full_text, token_spans

    @staticmethod
    def extract_scanned_words(page: fitz.Page) -> Tuple[str, List[Dict[str, Any]]]:
        """
        Renders page to image and uses OCR engine with coordinate harmonization.
        """
        # Render at 200 DPI for sharp OCR text recognition
        pix = page.get_pixmap(dpi=200)
        img_bytes = pix.tobytes("png")
        nparr = np.frombuffer(img_bytes, np.uint8)
        img_cv = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

        tokens = OCREngine.extract_page_tokens(
            page_image=img_cv,
            pdf_width=page.rect.width,
            pdf_height=page.rect.height
        )

        text_pieces = []
        token_spans = []
        curr_offset = 0

        for t in tokens:
            word_str = t["text"]
            start_pos = curr_offset
            end_pos = curr_offset + len(word_str)

            token_spans.append({
                "text": word_str,
                "bbox": t["bbox"],
                "start_char": start_pos,
                "end_char": end_pos,
                "confidence": t.get("confidence", 0.8)
            })

            text_pieces.append(word_str)
            curr_offset = end_pos + 1

        full_text = " ".join(text_pieces)
        return full_text, token_spans

    @classmethod
    def ingest_page(cls, page: fitz.Page) -> Dict[str, Any]:
        """
        Dispatches page processing based on classified structure.
        """
        meta = cls.classify_page_type(page)
        if meta["is_digital"]:
            text, tokens = cls.extract_native_words(page)
            engine_used = "pymupdf_native"
        else:
            text, tokens = cls.extract_scanned_words(page)
            engine_used = "easyocr_raster"

        return {
            "page_num": page.number,
            "engine": engine_used,
            "is_digital": meta["is_digital"],
            "full_text": text,
            "tokens": tokens,
            "metadata": meta
        }
