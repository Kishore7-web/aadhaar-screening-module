import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))
import cv2, numpy as np
from app.services.ocr_adapter import OCRAdapter

def test_ocr_normal():
    adapter = OCRAdapter()
    if not adapter.is_available():
        # fallback should still return structure
        img = np.ones((100,400,3), dtype=np.uint8)*255
        res = adapter.ocr_image(img)
        assert res is not None
        assert hasattr(res, 'text')
        return
    img = np.ones((100,400,3), dtype=np.uint8)*255
    cv2.putText(img, "Aarav Kumar", (10,50), cv2.FONT_HERSHEY_SIMPLEX, 1, (0,0,0),2)
    res = adapter.ocr_image(img)
    assert res.text is not None
    # confidence may be low but should have some
    assert res.confidence >=0

def test_ocr_empty():
    adapter = OCRAdapter()
    img = np.ones((100,100,3), dtype=np.uint8)*255
    res = adapter.ocr_image(img)
    # empty image may give empty text but should not crash
    assert res is not None
    assert res.engine is not None

def test_ocr_low_confidence():
    adapter = OCRAdapter()
    # very blurry image
    img = np.ones((100,400,3), dtype=np.uint8)*255
    cv2.putText(img, "BlurryText", (10,50), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (100,100,100),1)
    blurred = cv2.GaussianBlur(img, (15,15),0)
    res = adapter.ocr_image(blurred)
    assert res is not None
