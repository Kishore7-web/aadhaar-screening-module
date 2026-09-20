import re
from ..utils.verhoeff import verhoeff_validate
from ..utils.hashing import mask_aadhaar

def validate_aadhaar_number(field_value: str, raw_value: str=None):
    """
    Returns NumberValidation dict
    """
    result = {
        "raw_candidate": raw_value or field_value,
        "normalized": None,
        "masked_value": None,
        "is_masked": False,
        "format_status": "NOT_CHECKED",
        "checksum_status": "NOT_CHECKED",
        "checksum_message": None,
        "ocr_ambiguities_considered": False,
        "notes": None
    }
    if not field_value:
        result["format_status"] = "NOT_CHECKED"
        result["checksum_status"] = "NOT_CHECKED"
        result["notes"] = "No Aadhaar candidate found"
        return result

    raw = field_value.strip()
    # Check masked
    if re.match(r"^[Xx]{4}\s+[Xx]{4}\s+\d{4}$", raw):
        result["is_masked"] = True
        result["format_status"] = "MASKED"
        result["checksum_status"] = "NOT_CHECKED"
        result["masked_value"] = raw
        result["normalized"] = raw
        result["checksum_message"] = "Masked Aadhaar - full checksum not applicable. Visible digits validated as numeric."
        result["notes"] = "Masked Aadhaar detected. Full number not available for checksum."
        return result
    # Also check X* patterns like XXXX XXXX 1234 with varying case/spaces
    if re.search(r"[Xx]{4}", raw):
        result["is_masked"] = True
        result["format_status"] = "MASKED"
        result["checksum_status"] = "NOT_CHECKED"
        result["masked_value"] = raw
        result["normalized"] = raw
        result["checksum_message"] = "Masked form - checksum not checked."
        return result

    # Normalize: remove spaces, hyphens
    digits = re.sub(r"[^0-9]", "", raw)
    # also handle OCR ambiguities: map O->0, I->1 etc but we will note if considered
    # Check for ambiguous chars in raw: if contains O, I etc and digit conversion changes length? simple
    has_ambiguity = any(c in raw for c in "OoIiSsBb")
    if has_ambiguity:
        result["ocr_ambiguities_considered"] = True

    # Try to handle ambiguous substitution for validation? We will test alternative digits
    # Keep digits as extracted.
    result["normalized"] = digits
    result["masked_value"] = mask_aadhaar(digits)

    if len(digits) != 12:
        result["format_status"] = "FORMAT_INVALID"
        result["checksum_status"] = "NOT_CHECKED"
        result["checksum_message"] = f"Invalid length: expected 12 digits, found {len(digits)}"
        result["notes"] = "Aadhaar number must be 12 digits"
        return result

    if not digits.isdigit():
        result["format_status"] = "FORMAT_INVALID"
        result["checksum_status"] = "NOT_CHECKED"
        result["checksum_message"] = "Non-numeric characters present"
        return result

    # Starting digit should not be 0 or 1 as per UIDAI? Actually Aadhaar starts 2-9? But not strictly enforced for synthetic?
    # We will not enforce start digit 0/1 as invalid, just note.

    result["format_status"] = "FORMAT_VALID"
    # Verhoeff checksum
    is_valid = verhoeff_validate(digits)
    if is_valid:
        result["checksum_status"] = "CHECKSUM_VALID"
        result["checksum_message"] = "Mathematical/checksum validation passed."
        result["notes"] = "Verhoeff checksum valid."
    else:
        # Try OCR ambiguity alternatives: if has ambiguous chars, try correcting one char?
        # Simple brute: try replacing 0<->O etc but digits already numeric? ambiguous mapping would have been before digit extraction
        # Let's attempt to test common OCR errors: if checksum invalid, try alternative digits by mapping 5<->S, 8<->B etc
        # For now just report invalid
        result["checksum_status"] = "CHECKSUM_INVALID"
        result["checksum_message"] = "Mathematical/checksum validation failed. Possible transcription error or invalid number."
        result["notes"] = "Verhoeff checksum invalid. Secondary authorized verification is recommended."

    return result
