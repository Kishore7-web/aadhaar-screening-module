import sys, cv2, numpy as np
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))
from app.services.forensics import analyze_forensics

def test_clean():
    img = np.ones((600,800,3), dtype=np.uint8)*255
    cv2.putText(img, "Clean Document Test", (50,100), cv2.FONT_HERSHEY_SIMPLEX, 1,(0,0,0),2)
    res = analyze_forensics(img)
    assert res["analyzed"] is True
    assert res["overall_label"] in ["NO_SIGNIFICANT_SIGNAL","LOW_SIGNAL","SUSPICIOUS"]

def test_blurry():
    img = np.ones((600,800,3), dtype=np.uint8)*255
    cv2.putText(img, "Blurry", (50,100), cv2.FONT_HERSHEY_SIMPLEX, 1,(0,0,0),2)
    blurred = cv2.GaussianBlur(img, (21,21),0)
    res = analyze_forensics(blurred)
    assert res["analyzed"] is True

def test_recompressed():
    img = np.ones((600,800,3), dtype=np.uint8)*255
    cv2.rectangle(img, (100,100),(300,300),(0,0,0),2)
    _, enc = cv2.imencode('.jpg', img, [int(cv2.IMWRITE_JPEG_QUALITY), 30])
    dec = cv2.imdecode(enc, cv2.IMREAD_COLOR)
    res = analyze_forensics(dec)
    assert res["analyzed"] is True
