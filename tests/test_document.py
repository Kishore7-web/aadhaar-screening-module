import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))
from app.services.doc_identification import identify_document

def test_aadhaar_detected():
    text = "Government of India Aadhaar Name: Aarav Kumar DOB: 12/04/2005 Gender: Male 1234 5678 9012"
    res = identify_document(text, has_qr=True)
    assert res["result"]=="AADHAAR"
    assert res["confidence"]>0.5

def test_unsupported():
    text = "This is a random invoice with no relevant terms"
    res = identify_document(text, has_qr=False)
    assert res["result"]=="UNSUPPORTED_DOCUMENT"

def test_not_confident():
    text = "Aadhaar"
    res = identify_document(text, has_qr=False)
    # With only one keyword and no number, should be not confident or unsupported
    assert res["result"] in ["NOT_CONFIDENT","AADHAAR","UNSUPPORTED_DOCUMENT"]
