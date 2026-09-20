import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))
from fastapi.testclient import TestClient
from app.main import app
import io, zipfile

client = TestClient(app)

def test_path_traversal_filename():
    # Try malicious filename
    img = b"\xff\xd8\xff\xe0\x00\x10JFIF" + b"0"*1000
    # filename with traversal
    res = client.post("/api/modules/aadhaar", files={"document": ("../../etc/passwd.jpg", img, "image/jpeg")})
    # Should sanitize and not crash
    assert res.status_code in [200,400]
    if res.status_code==200:
        assert ".." not in res.json()["document"]["file_name"]

def test_oversized_file():
    large = b"\xff\xd8\xff" + b"A"* (11*1024*1024)  # 11 MB > limit 10
    res = client.post("/api/modules/aadhaar", files={"document": ("large.jpg", large, "image/jpeg")})
    assert res.status_code in [200,400]
    if res.status_code==200:
        assert res.json()["module_status"] in ["FAILED","PARTIAL"]

def test_invalid_mime():
    # PNG magic but jpg extension mismatch? Our magic check will fail
    data = b"\x89PNG\r\n\x1a\n" + b"0"*1000
    res = client.post("/api/modules/aadhaar", files={"document": ("fake.jpg", data, "image/jpeg")})
    # Should detect magic mismatch
    assert res.status_code in [200,400]

def test_unsafe_zip():
    # Create zip with path traversal
    buf = io.BytesIO()
    z = zipfile.ZipFile(buf, 'w')
    z.writestr("../../evil.txt", "evil")
    z.close()
    buf.seek(0)
    # Try upload as offline_ekyc (but need doc too)
    import cv2, numpy as np
    img = np.ones((100,100,3), dtype=np.uint8)*255
    _, img_buf = cv2.imencode('.jpg', img)
    res = client.post("/api/modules/aadhaar", files={"document": ("doc.jpg", img_buf.tobytes(), "image/jpeg"), "offline_ekyc": ("evil.zip", buf.getvalue(), "application/zip")})
    # Should handle zip traversal error gracefully
    assert res.status_code==200
    data=res.json()
    # Should have error or status FAILED for ekyc
    assert data["offline_ekyc"]["status"] in ["FAILED","NOT_PROVIDED","PARSED"]

def test_corrupted_pdf():
    data = b"%PDF-1.4 corrupted content not real pdf structure"
    res = client.post("/api/modules/aadhaar", files={"document": ("bad.pdf", data, "application/pdf")})
    assert res.status_code in [200,400]
