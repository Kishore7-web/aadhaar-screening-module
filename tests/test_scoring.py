import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))
from app.services.scoring_engine import calculate_scores
from app.services.evidence_engine import build_evidence

def make_evidence_high():
    # Simulate evidence with high mismatches
    evidence = [
        {"evidence_id":"E-AAD-001","source":"CONSISTENCY","category":"CONTRADICTION","finding":"Printed DOB differs","severity":"HIGH","confidence":0.85,"confidence_basis":"HEURISTIC","group":"CONSISTENCY","independent_source":True},
        {"evidence_id":"E-AAD-002","source":"FORENSICS","category":"IMAGE_MANIPULATION","finding":"Anomaly","severity":"MEDIUM","confidence":0.7,"confidence_basis":"HEURISTIC","group":"FORENSICS","independent_source":True},
    ]
    return evidence

def test_deterministic():
    evidence = make_evidence_high()
    scores1 = calculate_scores(evidence, [], {"overall_label":"GOOD","is_blurry":False,"is_low_quality":False,"blur_score":300}, {"status":"DETECTED"}, {"analyzed":True,"overall_label":"SUSPICIOUS","regions":[{"severity":"MEDIUM"}],"signals":["sig"]}, {"status":"NOT_CHECKED","has_reference":False}, {"status":"QR_PRESENT","decoded":True}, {"format_status":"FORMAT_VALID","checksum_status":"CHECKSUM_VALID"}, {"result":"AADHAAR"}, {"provided":False})
    scores2 = calculate_scores(evidence, [], {"overall_label":"GOOD","is_blurry":False,"is_low_quality":False,"blur_score":300}, {"status":"DETECTED"}, {"analyzed":True,"overall_label":"SUSPICIOUS","regions":[{"severity":"MEDIUM"}],"signals":["sig"]}, {"status":"NOT_CHECKED","has_reference":False}, {"status":"QR_PRESENT","decoded":True}, {"format_status":"FORMAT_VALID","checksum_status":"CHECKSUM_VALID"}, {"result":"AADHAAR"}, {"provided":False})
    assert scores1["integrity_score"] == scores2["integrity_score"]
    assert scores1["evidence_coverage"] == scores2["evidence_coverage"]

def test_clean_case():
    evidence = [
        {"evidence_id":"E-AAD-001","source":"QUALITY","category":"IMAGE_QUALITY","finding":"Good","severity":"INFO","confidence":0.7,"confidence_basis":"HEURISTIC","group":"QUALITY","independent_source":True},
        {"evidence_id":"E-AAD-002","source":"FORENSICS","category":"FORENSICS","finding":"No signal","severity":"INFO","confidence":0.6,"confidence_basis":"HEURISTIC","group":"FORENSICS","independent_source":True},
    ]
    scores = calculate_scores(evidence, [], {"overall_label":"GOOD","is_blurry":False,"is_low_quality":False,"blur_score":350}, {"status":"DETECTED"}, {"analyzed":True,"overall_label":"NO_SIGNIFICANT_SIGNAL","regions":[],"signals":[]}, {"status":"NOT_CHECKED","has_reference":False}, {"status":"QR_PRESENT","decoded":True}, {"format_status":"FORMAT_VALID","checksum_status":"CHECKSUM_VALID"}, {"result":"AADHAAR"}, {"provided":False})
    assert scores["integrity_score"] >= 80
    assert scores["coverage_sufficient"] is True

def test_low_coverage():
    evidence = []
    scores = calculate_scores(evidence, [], {"overall_label":"POOR","is_blurry":True,"is_low_quality":True,"blur_score":20}, {"status":"NOT_FOUND"}, {"analyzed":False,"overall_label":"ERROR","regions":[],"signals":[]}, {"status":"FACE_NOT_FOUND","has_reference":False}, {"status":"QR_NOT_PRESENT","decoded":False}, {"format_status":"NOT_CHECKED","checksum_status":"NOT_CHECKED"}, {"result":"NOT_CONFIDENT"}, {"provided":False})
    assert scores["evidence_coverage"] < 60
