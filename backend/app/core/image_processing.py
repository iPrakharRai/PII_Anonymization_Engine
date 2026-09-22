"""
OpenCV Preprocessing Pipeline.
Provides image enhancement for low-resolution scanned circulars,
including Hough Line deskewing, noise filtering, and adaptive binarization.
"""
import cv2
import numpy as np
from PIL import Image
from typing import Tuple

class ImagePreprocessor:
    """
    Enhances scanned document images before OCR layout analysis.
    Handles skew correction, noise suppression, and contrast normalization.
    """

    @staticmethod
    def estimate_skew_angle(image: np.ndarray) -> float:
        """
        Estimates the skew angle of the document using Hough Line Transform.
        """
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image.copy()

        # Edge detection
        edges = cv2.Canny(gray, 50, 150, apertureSize=3)
        lines = cv2.HoughLinesP(edges, 1, np.pi / 180, threshold=100, minLineLength=100, maxLineGap=10)

        if lines is None:
            return 0.0

        angles = []
        for line in lines:
            coords = line.flatten()
            if len(coords) < 4:
                continue
            x1, y1, x2, y2 = coords[:4]
            angle = np.degrees(np.arctan2(y2 - y1, x2 - x1))
            # Focus on horizontal text line candidates
            if abs(angle) < 45.0:
                angles.append(angle)

        if not angles:
            return 0.0

        median_angle = float(np.median(angles))
        return median_angle

    @staticmethod
    def deskew_image(image: np.ndarray, angle: float = None) -> Tuple[np.ndarray, float]:
        """
        Rotates image to correct skew around its center.
        """
        if angle is None:
            angle = ImagePreprocessor.estimate_skew_angle(image)

        if abs(angle) < 0.3:
            return image, 0.0  # Negligible skew

        (h, w) = image.shape[:2]
        center = (w // 2, h // 2)
        rotation_matrix = cv2.getRotationMatrix2D(center, angle, 1.0)
        deskewed = cv2.warpAffine(
            image, rotation_matrix, (w, h),
            flags=cv2.INTER_CUBIC,
            borderMode=cv2.BORDER_REPLICATE
        )
        return deskewed, angle

    @staticmethod
    def binarize_and_denoise(image: np.ndarray) -> np.ndarray:
        """
        Applies bilateral filtering and adaptive Gaussian thresholding
        to remove background bleed-through and shadows common in public circulars.
        """
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image.copy()

        # Denoise while keeping edges sharp
        denoised = cv2.bilateralFilter(gray, 9, 75, 75)

        # Adaptive thresholding for uneven lighting/photocopy gradients
        binary = cv2.adaptiveThreshold(
            denoised, 255,
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY,
            21, 11
        )
        return binary

    @staticmethod
    def preprocess_pipeline(image: np.ndarray) -> Tuple[np.ndarray, float]:
        """
        Complete enhancement pipeline: Deskew -> Binarize/Denoise.
        Returns processed image and detected skew angle.
        """
        deskewed, angle = ImagePreprocessor.deskew_image(image)
        enhanced = ImagePreprocessor.binarize_and_denoise(deskewed)
        return enhanced, angle
