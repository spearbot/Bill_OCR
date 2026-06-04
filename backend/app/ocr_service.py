import time
import logging
from typing import List, Dict, Any, Tuple
from PIL import Image
import numpy as np
from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class OCRService:
    def __init__(self):
        self._ocr = None
        logger.info("OCRService initialized")

    def _get_ocr(self):
        if self._ocr is None:
            logger.info("Loading PaddleOCR...")
            from paddleocr import PaddleOCR
            self._ocr = PaddleOCR(lang=settings.PADDLEOCR_LANG)
            logger.info("PaddleOCR loaded")
        return self._ocr

    def extract_text(self, image: Image.Image) -> Tuple[List[Dict], float]:
        start = time.time()
        try:
            img_array = np.array(image.convert("RGB"))
            ocr = self._get_ocr()
            results = ocr.ocr(img_array)

            lines = []
            total_conf = 0.0
            count = 0

            if isinstance(results, list):
                for page in results:
                    if not isinstance(page, list):
                        continue
                    for item in page:
                        if not isinstance(item, (list, tuple)) or len(item) != 2:
                            continue
                        bbox, (text, conf) = item
                        if text and text.strip():
                            conf_val = float(conf) if conf is not None else 0.0
                            lines.append({"text": str(text), "confidence": conf_val, "bbox": bbox})
                            total_conf += conf_val
                            count += 1

            avg_conf = total_conf / count if count > 0 else 0.0
            ms = (time.time() - start) * 1000
            logger.info(f"OCR: {ms:.0f}ms, {avg_conf:.2f}, {count} lines")
            return lines, avg_conf
        except Exception as e:
            logger.error(f"OCR failed: {e}", exc_info=True)
            raise

    def extract_text_from_pdf(self, pdf_bytes: bytes) -> Tuple[List[Dict], float]:
        from pdf2image import convert_from_bytes
        images = convert_from_bytes(pdf_bytes, dpi=300)
        all_lines = []
        all_confs = []
        for img in images:
            lines, conf = self.extract_text(img)
            all_lines.extend(lines)
            all_confs.append(conf)
        avg = sum(all_confs) / len(all_confs) if all_confs else 0.0
        return all_lines, avg
