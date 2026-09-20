import sys, io
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from fastapi.testclient import TestClient
from app.main import app
import cv2, numpy as np, qrcode
from PIL import Image

client = TestClient(app)

def test_health():
    res = client.get("/api/health")
    assert res.status_code==200
    assert res.json()["status"]=="ok"

def test_health_details():
    res = client.get("/api/health/details")
    assert res.status_code==200
    assert "python_version" in res.json()

def make_test_image():
    img = np.ones((600,900,3), dtype=np.uint8)*255
    cv2.putText(img, "Government of India", (250,40), cv2.FONT_HERSHEY_SIMPLEX, 0.7,(0,0,0),2)
    cv2.putText(img, "Aadhaar", (400,80), cv2.FONT_HERSHEY_SIMPLEX, 1,(0,0,0),2)
    cv2.putText(img, "Name: Aarav Kumar", (50,150), cv2.FONT_HERSHEY_SIMPLEX, 0.6,(0,0,0),1)
    cv2.putText(img, "DOB: 12/04/2005", (50,190), cv2.FONT_HERSHEY_SIMPLEX, 0.6,(0,0,0),1)
    cv2.putText(img, "Gender: Male", (50,230), cv2.FONT_HERSHEY_SIMPLEX, 0.6,(0,0,0),1)
    # Valid number
    from app.utils.verhoeff import verhoeff_generate
    base = "23456789011"
    full = base + verhoeff_generate(base)
    spaced = f"{full[:4]} {full[4:8]} {full[8:]}"
    cv2.putText(img, f"Aadhaar: {spaced}", (50,270), cv2.FONT_HERSHEY_SIMPLEX, 0.6,(0,0,0),1)
    # Add photo-like face
    cv2.ellipse(img, (800,200), (50,60),0,0,360,(200,150,120), -1)
    # Add QR
    qr_data = f'<PrintLetterBarcodeData uid="{full}" name="Aarav Kumar" gender="M" yob="2005"/>'
    qr = qrcode.QRCode(version=2, box_size=3, border=1)
    qr.add_data(qr_data)
    qr.make(fit=True)
    qr_img = qr.make_image(fill_color="black", back_color="white").convert("RGB")
    qr_img = qr_img.resize((120,120), Image.NEAREST)
    qr_cv = cv2.cvtColor(np.array(qr_img), cv2.COLOR_RGB2BGR)
    img[320:440, 750:870] = qr_cv
    # Encode
    _, buf = cv2.imencode('.jpg', img)
    return buf.tobytes(), full

def test_upload_success():
    img_bytes, full = make_test_image()
    res = client.post("/api/modules/aadhaar", files={"document": ("test.jpg", img_bytes, "image/jpeg")})
    assert res.status_code==200
    data = res.json()
    assert data["schema_version"]=="1.0"
    assert data["case_id"] is not None
    assert data["scores"]["integrity_score"] is not None
    assert data["screening"]["status"] in ["CLEAR","LOW_CONCERN","REVIEW","HIGH_REVIEW","INCONCLUSIVE"]
    # Check evidence present
    assert isinstance(data["evidence"], list)
    assert isinstance(data["audit"]["document_hash"], str)

def test_upload_invalid_file():
    res = client.post("/api/modules/aadhaar", files={"document": ("test.txt", b"not an image", "text/plain")})
    # Should handle gracefully, may return 200 with FAILED status or 400?
    # Our pipeline returns FAILED status but not crash
    assert res.status_code in [200,400]
    if res.status_code==200:
        assert res.json()["module_status"] in ["FAILED","PARTIAL","COMPLETE"]

def test_missing_file():
    res = client.post("/api/modules/aadhaar", files={})
    assert res.status_code==422  # validation error

def test_upload_with_face():
    img_bytes, _ = make_test_image()
    # create ref face
    ref = np.ones((300,300,3), dtype=np.uint8)*255
    cv2.ellipse(ref, (150,150),(80,100),0,0,360,(200,150,120),-1)
    cv2.circle(ref, (120,130),15,(0,0,0),-1)
    cv2.circle(ref, (180,130),15,(0,0,0),-1)
    _, ref_buf = cv2.imencode('.jpg', ref)
    res = client.post("/api/modules/aadhaar", files={"document": ("test.jpg", img_bytes, "image/jpeg"), "reference_face": ("ref.jpg", ref_buf.tobytes(), "image/jpeg")})
    assert res.status_code==200
    data = res.json()
    assert data["biometric"]["has_reference"] is True

def test_case_retrieval():
    img_bytes,_ = make_test_image()
    res = client.post("/api/modules/aadhaar", files={"document": ("test.jpg", img_bytes, "image/jpeg")})
    case_id = res.json()["case_id"]
    res2 = client.get(f"/api/cases/{case_id}")
    assert res2.status_code==200
    assert res2.json()["case_id"]==case_id

def test_cases_list():
    res = client.get("/api/cases")
    assert res.status_code==200
    assert "cases" in res.json()
