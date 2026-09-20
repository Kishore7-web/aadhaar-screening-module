import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))
import cv2, numpy as np, qrcode
from PIL import Image
from app.services.qr_analysis import detect_and_decode_qr, compare_qr_printed, parse_qr_data

def make_qr_image(data, size=300):
    qr = qrcode.QRCode(version=2, box_size=4, border=1)
    qr.add_data(data)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white").convert("RGB")
    img = img.resize((size,size), Image.NEAREST)
    cv = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)
    # embed in larger white canvas
    canvas = np.ones((500,500,3), dtype=np.uint8)*255
    canvas[100:100+size, 100:100+size] = cv
    return canvas

def test_qr_detected():
    data = '<PrintLetterBarcodeData uid="123456789012" name="Aarav Kumar" gender="M" yob="2005"/>'
    canvas = make_qr_image(data)
    res = detect_and_decode_qr([{"image":canvas, "page":1}])
    assert res["status"]=="QR_PRESENT"
    assert res["decoded"] is True
    assert res["fields"].get("name") is not None

def test_qr_not_present():
    canvas = np.ones((500,500,3), dtype=np.uint8)*255
    cv2.putText(canvas, "No QR here", (50,250), cv2.FONT_HERSHEY_SIMPLEX, 1,(0,0,0),2)
    res = detect_and_decode_qr([{"image":canvas, "page":1}])
    assert res["status"]=="QR_NOT_PRESENT"

def test_qr_match():
    fields = {"name":{"value":"Aarav Kumar"},"dob":{"value":"12/04/2005"},"gender":{"value":"MALE"},"aadhaar_number":{"value":"1234 5678 9012"}}
    qr_fields = {"name":"Aarav Kumar","dob":"12/04/2005","gender":"MALE","uid":"1234 5678 9012"}
    comp = compare_qr_printed(fields, qr_fields)
    assert comp["overall"]=="MATCH"

def test_qr_mismatch():
    fields = {"name":{"value":"Aarav Kumar"},"dob":{"value":"12/04/2005"},"gender":{"value":"MALE"},"aadhaar_number":{"value":"1234 5678 9012"}}
    qr_fields = {"name":"Aarav Kumar","dob":"12/04/2004","gender":"MALE","uid":"1234 5678 9012"}
    comp = compare_qr_printed(fields, qr_fields)
    assert comp["mismatches"]==1
    assert comp["overall"]=="MISMATCH"
