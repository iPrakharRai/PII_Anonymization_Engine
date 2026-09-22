"""
Coordinate Harmonization & Geometry Operations.
Normalizes OCR tokens, image coordinates, and PDF points into standardized (x0, y0, x1, y1) tuples.
"""
from typing import Tuple, List, Dict, Any
import fitz

class CoordinateHarmonizer:
    """
    Converts and aligns coordinates across different spatial reference frames:
    - PDF native point space (72 points/inch)
    - High-resolution raster space (DPI-scaled, e.g. 150/300 DPI)
    - Rotated and translated layout bounding boxes
    """

    @staticmethod
    def scale_image_to_pdf(
        box: Tuple[float, float, float, float],
        img_width: float,
        img_height: float,
        pdf_width: float,
        pdf_height: float,
        padding: float = 1.5
    ) -> Tuple[float, float, float, float]:
        """
        Scales an image bounding box (x0, y0, x1, y1) to true PDF page points.
        Adds safety padding to ensure complete glyph ink coverage.
        """
        x_scale = pdf_width / img_width if img_width > 0 else 1.0
        y_scale = pdf_height / img_height if img_height > 0 else 1.0

        x0 = max(0.0, (box[0] * x_scale) - padding)
        y0 = max(0.0, (box[1] * y_scale) - padding)
        x1 = min(pdf_width, (box[2] * x_scale) + padding)
        y1 = min(pdf_height, (box[3] * y_scale) + padding)

        return (x0, y0, x1, y1)

    @staticmethod
    def normalize_box(
        box: Tuple[float, float, float, float],
        page_width: float,
        page_height: float
    ) -> Tuple[float, float, float, float]:
        """Ensures x0 <= x1, y0 <= y1 and clamps within page bounds."""
        x0 = min(box[0], box[2])
        x1 = max(box[0], box[2])
        y0 = min(box[1], box[3])
        y1 = max(box[1], box[3])

        return (
            max(0.0, min(x0, page_width)),
            max(0.0, min(y0, page_height)),
            max(0.0, min(x1, page_width)),
            max(0.0, min(y1, page_height))
        )

    @staticmethod
    def to_fitz_rect(box: Tuple[float, float, float, float], padding: float = 1.0) -> fitz.Rect:
        """Converts tuple to fitz.Rect with optional padding."""
        return fitz.Rect(
            box[0] - padding,
            box[1] - padding,
            box[2] + padding,
            box[3] + padding
        )

    @staticmethod
    def merge_overlapping_boxes(
        boxes: List[Tuple[float, float, float, float]],
        iou_threshold: float = 0.2
    ) -> List[Tuple[float, float, float, float]]:
        """Merges adjacent or overlapping bounding boxes."""
        if not boxes:
            return []

        rects = [fitz.Rect(*b) for b in boxes]
        merged = []

        while rects:
            curr = rects.pop(0)
            merged_any = False
            for i, other in enumerate(rects):
                if curr.intersects(other):
                    curr = curr | other
                    rects.pop(i)
                    merged_any = True
                    break
            if merged_any:
                rects.insert(0, curr)
            else:
                merged.append((curr.x0, curr.y0, curr.x1, curr.y1))

        return merged
