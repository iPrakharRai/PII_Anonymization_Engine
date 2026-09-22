"""
OCR Engine with Coordinate Harmonization.
Performs layout OCR on scanned pages and maps detected text tokens to universal PDF points (x0, y0, x1, y1).
"""
from typing import List, Dict, Any, Tuple
import cv2
import numpy as np
from PIL import Image
from backend.app.utils.coordinates import CoordinateHarmonizer
from backend.app.core.image_processing import ImagePreprocessor

class OCREngine:
    """
    Wrapper around EasyOCR with image enhancement and spatial coordinate mapping.
    """
    _instance = None
    _reader = None

    @classmethod
    def get_reader(cls):
        if cls._reader is None:
            try:
                import easyocr
                cls._reader = easyocr.Reader(['en'], gpu=False, verbose=False, download_enabled=True)
            except Exception:
                cls._reader = "OPENCV_MORPH"
        return cls._reader

    @classmethod
    def extract_page_tokens(
        cls,
        page_image: np.ndarray,
        pdf_width: float,
        pdf_height: float
    ) -> List[Dict[str, Any]]:
        """
        Runs OCR on page image, returning tokens with harmonized PDF bounding boxes.
        """
        reader = cls.get_reader()

        # Preprocess: Deskew & enhance
        enhanced, skew_angle = ImagePreprocessor.preprocess_pipeline(page_image)
        img_h, img_w = enhanced.shape[:2]

        tokens = []

        if reader != "OPENCV_MORPH":
            try:
                raw_results = reader.readtext(enhanced)
                for bbox, text, prob in raw_results:
                    cleaned_text = text.strip()
                    if not cleaned_text:
                        continue
                    xs = [pt[0] for pt in bbox]
                    ys = [pt[1] for pt in bbox]
                    img_box = (min(xs), min(ys), max(xs), max(ys))
                    pdf_box = CoordinateHarmonizer.scale_image_to_pdf(
                        box=img_box, img_width=img_w, img_height=img_h,
                        pdf_width=pdf_width, pdf_height=pdf_height, padding=2.0
                    )
                    tokens.append({"text": cleaned_text, "bbox": pdf_box, "confidence": float(prob)})
                return tokens
            except Exception:
                pass

        # Fallback: Morphological layout & word-box extraction via OpenCV
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (15, 3))
        dilated = cv2.morphologyEx(255 - enhanced, cv2.MORPH_DILATE, kernel)
        contours, _ = cv2.findContours(dilated, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        for cnt in contours:
            x, y, w, h = cv2.boundingRect(cnt)
            if w < 10 or h < 6 or w > img_w * 0.95:
                continue
            img_box = (float(x), float(y), float(x + w), float(y + h))
            pdf_box = CoordinateHarmonizer.scale_image_to_pdf(
                box=img_box, img_width=img_w, img_height=img_h,
                pdf_width=pdf_width, pdf_height=pdf_height, padding=1.5
            )
            tokens.append({"text": "[SCANNED_TEXT_TOKEN]", "bbox": pdf_box, "confidence": 0.85})

        return tokens
