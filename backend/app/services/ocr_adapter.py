import time
import cv2
import numpy as np
from typing import List, Dict, Any

class OCRResult:
    def __init__(self, text="", confidence=0, boxes=None, engine="unknown", page=1, status="DONE"):
        self.text = text
        self.confidence = confidence
        self.boxes = boxes or []
        self.engine = engine
        self.page = page
        self.status = status

class OCREngine:
    def ocr(self, image, page=1) -> OCRResult:
        raise NotImplementedError

class RapidOCREngine(OCREngine):
    def __init__(self):
        self.engine = None
        self.available = False
        self.name = "rapidocr_onnxruntime"
        try:
            from rapidocr_onnxruntime import RapidOCR
            self.engine = RapidOCR()
            self.available = True
        except Exception as e:
            print(f"RapidOCR init failed: {e}")
            self.available = False

    def ocr(self, image, page=1) -> OCRResult:
        if not self.available or self.engine is None:
            return OCRResult(text="", confidence=0, engine=self.name, page=page, status="NOT_AVAILABLE")
        try:
            start = time.time()
            # RapidOCR expects BGR or RGB? It handles
            result, elapse = self.engine(image)
            # result is list of [bbox, text, conf]
            texts = []
            confidences = []
            boxes = []
            if result:
                for item in result:
                    try:
                        bbox, txt, conf = item
                        # conf may be string
                        conf_f = float(conf) if isinstance(conf, str) else float(conf)
                        texts.append(txt)
                        confidences.append(conf_f)
                        # bbox is 4 points, convert to [x,y,w,h]
                        # compute bounding rect
                        pts = np.array(bbox, dtype=np.int32)
                        x, y, w, h = cv2.boundingRect(pts)
                        boxes.append({"text": txt, "confidence": conf_f, "bbox": [int(x),int(y),int(w),int(h)], "poly": bbox})
                    except Exception as e:
                        continue
            full_text = " ".join(texts) if texts else ""
            # also join with newlines heuristically? Keep space.
            # For better field extraction, we want newlines where vertical gaps
            # We'll create text with newlines sorted by y
            if boxes:
                # sort by y then x
                sorted_boxes = sorted(boxes, key=lambda b: (b["bbox"][1], b["bbox"][0]))
                # group lines by y proximity
                lines = []
                current_line = []
                last_y = None
                for b in sorted_boxes:
                    y = b["bbox"][1]
                    if last_y is None or abs(y - last_y) < 20:
                        current_line.append(b)
                    else:
                        # sort current line by x
                        current_line = sorted(current_line, key=lambda x: x["bbox"][0])
                        lines.append(" ".join(c["text"] for c in current_line))
                        current_line = [b]
                    last_y = y
                if current_line:
                    current_line = sorted(current_line, key=lambda x: x["bbox"][0])
                    lines.append(" ".join(c["text"] for c in current_line))
                full_text = "\n".join(lines)

            avg_conf = float(np.mean(confidences)) if confidences else 0.0
            return OCRResult(text=full_text, confidence=avg_conf, boxes=boxes, engine=self.name, page=page, status="DONE")
        except Exception as e:
            return OCRResult(text="", confidence=0, engine=self.name, page=page, status=f"ERROR:{e}")

class FallbackOCREngine(OCREngine):
    """Deterministic fallback that returns NOT_AVAILABLE but preserves pipeline"""
    def __init__(self):
        self.name = "fallback"
    def ocr(self, image, page=1) -> OCRResult:
        return OCRResult(text="", confidence=0, engine=self.name, page=page, status="NOT_AVAILABLE")

class OCRAdapter:
    def __init__(self):
        self.primary = RapidOCREngine()
        self.fallback = FallbackOCREngine()
        self.current_engine_name = self.primary.name if self.primary.available else self.fallback.name

    def is_available(self):
        return self.primary.available

    def ocr_image(self, image, page=1) -> OCRResult:
        res = self.primary.ocr(image, page)
        if res.status == "NOT_AVAILABLE" or res.status.startswith("ERROR"):
            # try fallback (which just returns not available)
            fb = self.fallback.ocr(image, page)
            # preserve primary error status
            return res
        return res

    def ocr_images(self, images) -> List[OCRResult]:
        results = []
        for item in images:
            img = item["image"]
            page = item["page"]
            r = self.ocr_image(img, page)
            results.append(r)
        return results

    def combined_text(self, results: List[OCRResult]) -> str:
        return "\n".join(r.text for r in results if r.text)

    def avg_confidence(self, results: List[OCRResult]) -> float:
        confs = [r.confidence for r in results if r.confidence>0]
        return float(np.mean(confs)) if confs else 0.0

# Global adapter instance for FastAPI health checks
ocr_adapter = OCRAdapter()
