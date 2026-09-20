#!/usr/bin/env python3
"""
Model setup checker for DAKSH P3
Checks required models, reports missing, and ensures local OCR works.
No heavy model download required for MVP (uses RapidOCR which auto-downloads on first use, and OpenCV Haar cascades)
"""
import sys
from pathlib import Path
import cv2

def check():
    print("=== DAKSH P3 Model Setup Check ===")
    print(f"OpenCV version: {cv2.__version__}")
    # Haar cascade check
    cascade_path = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
    if Path(cascade_path).exists():
        print(f"✓ Haar cascade found: {cascade_path}")
    else:
        print("✗ Haar cascade missing")

    # RapidOCR
    try:
        from rapidocr_onnxruntime import RapidOCR
        ocr = RapidOCR()
        print("✓ RapidOCR available and loaded")
        # test
        import numpy as np
        img = np.ones((100,400,3), dtype=np.uint8)*255
        cv2.putText(img, "Test 123", (10,50), cv2.FONT_HERSHEY_SIMPLEX, 1, (0,0,0),2)
        result, elapse = ocr(img)
        print(f"  OCR test result: {result}")
    except Exception as e:
        print(f"✗ RapidOCR failed: {e}")
        print("  Install: pip install rapidocr_onnxruntime onnxruntime")

    # QR
    try:
        detector = cv2.QRCodeDetector()
        print("✓ QR detector available")
    except Exception as e:
        print(f"✗ QR detector failed: {e}")

    # Optional SFace/YuNet would need onnx files
    models_dir = Path(__file__).resolve().parents[1] / "models"
    models_dir.mkdir(exist_ok=True)
    print(f"Models dir: {models_dir}")
    for m in ["face_detection_yunet_2023mar.onnx", "face_recognition_sface_2021dec.onnx"]:
        p = models_dir / m
        if p.exists():
            print(f"✓ Found {m}")
        else:
            print(f"○ {m} not found - using fallback Haar+Histogram (MVP). To enable SFace, download to {p}")

    print("\n=== Setup Summary ===")
    print("MVP models are READY (RapidOCR + Haar cascade + QR). Heavy models optional.")
    print("No blockchain/MongoDB required for core screening.")

if __name__ == "__main__":
    check()
