import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from app.services.number_validation import validate_aadhaar_number
from app.utils.verhoeff import verhoeff_validate, verhoeff_generate

def test_valid_aadhaar():
    # generate valid
    base = "23456789012"
    # we know 11+1? Generate 11 and compute check
    base11 = "23456789012"[:11]  # actually need 11
    base11 = "23456789012"[-11:]
    # Use known valid generation
    from app.utils.verhoeff import verhoeff_generate
    # generate full
    base11 = "23456789011"
    check = verhoeff_generate(base11)
    full = base11 + check
    assert len(full)==12
    assert verhoeff_validate(full) is True
    res = validate_aadhaar_number(full, full)
    assert res["format_status"]=="FORMAT_VALID"
    assert res["checksum_status"]=="CHECKSUM_VALID"

def test_invalid_length():
    res = validate_aadhaar_number("1234567890", "1234567890")
    assert res["format_status"]=="FORMAT_INVALID"

def test_invalid_characters():
    res = validate_aadhaar_number("1234 ABCD 9012", "1234 ABCD 9012")
    assert res["format_status"] in ["FORMAT_INVALID","MASKED"] or res["checksum_status"]=="NOT_CHECKED"

def test_checksum_invalid():
    # take valid and corrupt last digit
    base11 = "23456789011"
    check = verhoeff_generate(base11)
    full = base11+check
    # corrupt
    bad = full[:-1] + str((int(full[-1])+1)%10)
    # ensure bad checksum
    if verhoeff_validate(bad):
        bad = full[:-1] + str((int(full[-1])+2)%10)
    assert verhoeff_validate(bad) is False
    res = validate_aadhaar_number(bad, bad)
    assert res["checksum_status"]=="CHECKSUM_INVALID"

def test_masked():
    res = validate_aadhaar_number("XXXX XXXX 1234", "XXXX XXXX 1234")
    assert res["is_masked"] is True
    assert res["format_status"]=="MASKED"
    assert res["checksum_status"]=="NOT_CHECKED"

def test_masked_not_invalid():
    # masked should not be considered invalid
    res = validate_aadhaar_number("XXXX XXXX 9012", "XXXX XXXX 9012")
    assert res["format_status"]=="MASKED"

def test_ocr_ambiguity():
    # contains O
    res = validate_aadhaar_number("1234 5678 90O2", "1234 5678 90O2")
    assert res["ocr_ambiguities_considered"] is True
