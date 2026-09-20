import re

AADHAAR_KEYWORDS = [
    "aadhaar", "aadhar", "uidai", "government of india", "govt of india",
    "enrolment", "enrollment", "vid", "uid", "dob", "yob", "gender", "male", "female"
]

def identify_document(ocr_text: str, has_qr: bool, image=None):
    text_lower = ocr_text.lower() if ocr_text else ""
    keywords_found = []
    for kw in AADHAAR_KEYWORDS:
        if kw in text_lower:
            keywords_found.append(kw)

    signals = []
    # Signal 1: keyword count
    kw_score = len(keywords_found)

    # Signal 2: Aadhaar number pattern (12 digits or masked)
    has_number = False
    import re
    digits_pattern = re.search(r"\d{4}\s+\d{4}\s+\d{4}", ocr_text or "")
    masked_pattern = re.search(r"[Xx]{4}\s+[Xx]{4}\s+\d{4}", ocr_text or "")
    spaced12 = re.search(r"\d{12}", ocr_text or "")
    if digits_pattern or masked_pattern or spaced12:
        has_number = True
        signals.append("AADHAAR_NUMBER_PATTERN")

    # Signal 3: DOB pattern
    dob_pattern = re.search(r"\d{2}[/-]\d{2}[/-]\d{4}", ocr_text or "") or re.search(r"dob", text_lower) or re.search(r"year of birth", text_lower) or re.search(r"yob", text_lower)
    if dob_pattern:
        signals.append("DOB_PATTERN")

    # Signal 4: QR presence
    if has_qr:
        signals.append("QR_PRESENT")

    # Signal 5: gender
    if "male" in text_lower or "female" in text_lower:
        signals.append("GENDER_PRESENT")

    # Signal 6: address cues
    if "address" in text_lower or "s/o" in text_lower or "d/o" in text_lower or "w/o" in text_lower:
        signals.append("ADDRESS_CUE")

    # Decision logic
    # Require at least 2 strong signals
    strong = 0
    if kw_score >= 2:
        strong += 1
        signals.append(f"KEYWORDS_{kw_score}")
    if has_number:
        strong += 1
    if has_qr:
        strong += 1
    if dob_pattern:
        strong += 0.5

    if strong >= 2.5:
        result = "AADHAAR"
        confidence = min(0.95, 0.6 + strong*0.1)
    elif strong >= 1.5:
        result = "AADHAAR"
        confidence = 0.65
    elif strong >= 1:
        result = "NOT_CONFIDENT"
        confidence = 0.45
    else:
        result = "UNSUPPORTED_DOCUMENT"
        confidence = 0.7

    # Variant classification
    variant = "unknown"
    if masked_pattern:
        variant = "masked"
    elif "e-aadhaar" in text_lower or "e aadhaar" in text_lower:
        variant = "e_aadhaar"
    elif "pvc" in text_lower:
        variant = "pvc"
    else:
        # heuristic based on image
        variant = "physical" if result == "AADHAAR" else "unknown"

    # If ocr_text empty, mark not_confident
    if not ocr_text or len(ocr_text.strip()) < 10:
        if result == "AADHAAR":
            result = "NOT_CONFIDENT"
            confidence = 0.4

    return {
        "result": result,
        "confidence": round(float(confidence),3),
        "confidence_basis": "HEURISTIC",
        "variant": variant,
        "signals": signals,
        "keywords_found": keywords_found,
        "notes": f"Keyword matches: {kw_score}, has_number: {has_number}, has_qr: {has_qr}"
    }
