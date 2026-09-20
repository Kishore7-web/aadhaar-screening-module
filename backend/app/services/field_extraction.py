import re
from datetime import datetime

def normalize_spaces(s):
    return re.sub(r"\s+", " ", s).strip() if s else s

def extract_fields(ocr_text: str, ocr_results=None):
    fields = {}
    text = ocr_text or ""
    text_lower = text.lower()

    # Helper to create field
    def make_field(value, raw, normalized, confidence, basis, status, sources, bbox=None, page=1, notes=None):
        # masked value
        masked = None
        if value and "aadhaar" in notes.lower() if notes else False:
            pass
        return {
            "value": value,
            "raw_value": raw,
            "normalized_value": normalized,
            "masked_value": masked,
            "confidence": confidence,
            "confidence_basis": basis,
            "status": status,
            "sources": sources,
            "bounding_box": bbox,
            "page": page,
            "notes": notes,
            "consistency": None
        }

    # Estimate confidence from OCR results avg
    avg_conf = 0.0
    if ocr_results:
        confs = [r.confidence for r in ocr_results if r.confidence>0]
        if confs:
            avg_conf = float(sum(confs)/len(confs))
    if avg_conf==0:
        avg_conf = 0.5 if text.strip() else 0.0

    # Find bounding boxes for fields heuristically: search boxes for field text
    box_map = {}
    if ocr_results:
        for r in ocr_results:
            for b in r.boxes:
                box_map[b["text"].lower()] = b

    def find_box_for_value(val):
        if not val or not box_map:
            return None
        val_lower = val.lower()[:20]
        for k,b in box_map.items():
            if val_lower in k or k in val_lower:
                return b["bbox"]
        return None

    # Name extraction: look for pattern "Name" or assume first line with alphabets?
    name_val = None
    name_raw = None
    # Search for "Name" label
    name_match = re.search(r"(?:name|naam)\s*[:\-]?\s*([A-Za-z ]{3,40})", text, re.IGNORECASE)
    if name_match:
        name_raw = name_match.group(1).strip()
        name_val = normalize_spaces(name_raw.title())
    else:
        # fallback: find line with 2-3 words capitalized near top
        lines = [l.strip() for l in text.split("\n") if l.strip()]
        # filter lines containing only letters and spaces, length 3-40, and not containing keywords
        candidates = []
        for line in lines[:5]:
            if re.match(r"^[A-Za-z ]{4,40}$", line) and len(line.split())>=2 and not any(k in line.lower() for k in ["government","india","aadhaar","uidai","dob","gender","address"]):
                candidates.append(line)
        if candidates:
            name_raw = candidates[0]
            name_val = normalize_spaces(name_raw.title())

    status_name = "DETECTED" if name_val else "NOT_FOUND"
    conf_name = round(avg_conf,3) if name_val else 0.0
    fields["name"] = {
        "value": name_val,
        "raw_value": name_raw,
        "normalized_value": name_val,
        "masked_value": None,
        "confidence": conf_name,
        "confidence_basis": "OCR_ENGINE" if avg_conf>0 else "HEURISTIC",
        "status": status_name,
        "sources": [{"type":"OCR","confidence":conf_name}] if name_val else [],
        "bounding_box": find_box_for_value(name_val) if name_val else None,
        "page": 1,
        "notes": "Extracted via label or line heuristic" if name_val else "No name pattern found",
        "consistency": None
    }

    # DOB extraction: patterns
    dob_val = None
    dob_raw = None
    dob_normalized = None
    dob_match = re.search(r"(\d{2}[/\-\.]\d{2}[/\-\.]\d{4})", text)
    yob_match = re.search(r"(?:year of birth|yob|dob)[:\s]*(\d{4})", text, re.IGNORECASE)
    dob_label_match = re.search(r"dob\s*[:\-]?\s*(\d{2}[/\-\.]\d{2}[/\-\.]\d{4})", text, re.IGNORECASE)
    # also DOB dob: 12/04/2005
    if dob_label_match:
        dob_raw = dob_label_match.group(1)
        dob_val = dob_raw
    elif dob_match:
        dob_raw = dob_match.group(1)
        dob_val = dob_raw
    elif yob_match:
        dob_raw = yob_match.group(1)
        dob_val = dob_raw  # year only

    if dob_val:
        # normalize to YYYY-MM-DD if full date else year
        normalized = None
        try:
            if "/" in dob_val or "-" in dob_val:
                # try parse
                for fmt in ["%d/%m/%Y","%d-%m-%Y","%d.%m.%Y","%d/%m/%y"]:
                    try:
                        dt = datetime.strptime(dob_val.replace(".","/").replace("-","/"), fmt)
                        normalized = dt.strftime("%Y-%m-%d")
                        break
                    except:
                        continue
                if not normalized:
                    # manual
                    parts = re.split(r"[/\-\.]", dob_val)
                    if len(parts)==3:
                        normalized = f"{parts[2]}-{parts[1].zfill(2)}-{parts[0].zfill(2)}"
            else:
                # year
                if re.match(r"^\d{4}$", dob_val):
                    normalized = dob_val
            dob_normalized = normalized or dob_val
        except:
            dob_normalized = dob_val

    fields["dob"] = {
        "value": dob_val,
        "raw_value": dob_raw,
        "normalized_value": dob_normalized,
        "masked_value": None,
        "confidence": round(avg_conf,3) if dob_val else 0.0,
        "confidence_basis": "OCR_ENGINE" if avg_conf>0 else "HEURISTIC",
        "status": "DETECTED" if dob_val else "NOT_FOUND",
        "sources": [{"type":"OCR","confidence": round(avg_conf,3)}] if dob_val else [],
        "bounding_box": find_box_for_value(dob_val) if dob_val else None,
        "page": 1,
        "notes": "DOB pattern matched" if dob_val else "No DOB pattern",
        "consistency": None
    }
    # Also alias yob
    fields["year_of_birth"] = {
        "value": dob_normalized if dob_normalized and len(dob_normalized)==4 else (dob_normalized[:4] if dob_normalized and "-" in dob_normalized else None),
        "raw_value": dob_raw,
        "normalized_value": dob_normalized if dob_normalized and len(dob_normalized)==4 else None,
        "masked_value": None,
        "confidence": round(avg_conf,3) if dob_val else 0.0,
        "confidence_basis": "OCR_ENGINE",
        "status": "DETECTED" if dob_val else "NOT_FOUND",
        "sources": [{"type":"OCR","confidence": round(avg_conf,3)}] if dob_val else [],
        "bounding_box": None,
        "page": 1,
        "notes": None,
        "consistency": None
    }

    # Gender
    gender_val = None
    gender_raw = None
    if re.search(r"\bfemale\b", text, re.IGNORECASE):
        gender_val = "FEMALE"
        gender_raw = "Female"
    elif re.search(r"\bmale\b", text, re.IGNORECASE):
        # need to ensure not female
        if not re.search(r"female", text, re.IGNORECASE):
            gender_val = "MALE"
            gender_raw = "Male"
        else:
            # if both, decide female prevails? But male substring in female would have triggered female already
            gender_val = "FEMALE"
            gender_raw = "Female"
    elif re.search(r"gender\s*[:\-]?\s*(male|female|others)", text, re.IGNORECASE):
        m = re.search(r"gender\s*[:\-]?\s*(male|female|others)", text, re.IGNORECASE)
        gender_val = m.group(1).upper()
        gender_raw = m.group(1)

    fields["gender"] = {
        "value": gender_val,
        "raw_value": gender_raw,
        "normalized_value": gender_val,
        "masked_value": None,
        "confidence": round(avg_conf,3) if gender_val else 0.0,
        "confidence_basis": "OCR_ENGINE",
        "status": "DETECTED" if gender_val else "NOT_FOUND",
        "sources": [{"type":"OCR","confidence": round(avg_conf,3)}] if gender_val else [],
        "bounding_box": find_box_for_value(gender_val) if gender_val else None,
        "page": 1,
        "notes": None,
        "consistency": None
    }

    # Aadhaar number
    aadhaar_val = None
    aadhaar_raw = None
    masked = False
    # patterns
    # 1. masked XXXX XXXX 1234
    masked_m = re.search(r"[Xx]{4}\s+[Xx]{4}\s+\d{4}", text)
    # 2. 4-4-4 digits
    spaced_m = re.search(r"\d{4}\s+\d{4}\s+\d{4}", text)
    # 3. continuous 12
    cont_m = re.search(r"(?<!\d)\d{12}(?!\d)", text)
    if masked_m:
        aadhaar_raw = masked_m.group()
        aadhaar_val = aadhaar_raw
        masked = True
    elif spaced_m:
        aadhaar_raw = spaced_m.group()
        aadhaar_val = re.sub(r"\s+", "", aadhaar_raw)  # continuous?
        # keep spaced version as value? We'll provide normalized without spaces but masked will show last 4
        # Actually store raw with spaces
        aadhaar_val = spaced_m.group()
    elif cont_m:
        aadhaar_raw = cont_m.group()
        aadhaar_val = cont_m.group()
        # format as spaced for display?
        spaced = f"{aadhaar_val[:4]} {aadhaar_val[4:8]} {aadhaar_val[8:]}"
        #keep original

    # Handle OCR ambiguities: O->0, I->1 etc not yet; leave raw

    status_aadhaar = "NOT_FOUND"
    if aadhaar_val:
        if masked:
            status_aadhaar = "MASKED"
        else:
            status_aadhaar = "DETECTED"

    fields["aadhaar_number"] = {
        "value": aadhaar_val,
        "raw_value": aadhaar_raw,
        "normalized_value": aadhaar_val.replace(" ","") if aadhaar_val and not masked else aadhaar_val,
        "masked_value": None, # will be filled by hashing util
        "confidence": round(avg_conf,3) if aadhaar_val else 0.0,
        "confidence_basis": "OCR_ENGINE",
        "status": status_aadhaar,
        "sources": [{"type":"OCR","confidence": round(avg_conf,3)}] if aadhaar_val else [],
        "bounding_box": find_box_for_value(aadhaar_raw) if aadhaar_raw else None,
        "page": 1,
        "notes": "Masked Aadhaar detected" if masked else ("Aadhaar pattern found" if aadhaar_val else "No Aadhaar pattern"),
        "consistency": None
    }

    # Address: look for "Address:" label and capture following lines
    address_val = None
    address_raw = None
    addr_match = re.search(r"address\s*[:\-]?\s*(.+)", text, re.IGNORECASE | re.DOTALL)
    if addr_match:
        # capture until next keyword or end, limit 200 chars
        raw = addr_match.group(1).strip()
        # trim at next field-like keyword? e.g., Aadhaar number appears after address
        # If raw contains 4-4-4 number, split before it
        if spaced_m:
            # cut before aadhaar number position
            idx = raw.find(spaced_m.group()) if spaced_m else -1
            if idx>0:
                raw = raw[:idx].strip()
        # also cut at QR or DOB? keep simple
        # Take up to 3 lines
        lines = raw.split("\n")
        raw = " ".join(lines[:3])[:250]
        address_raw = raw.strip()
        address_val = normalize_spaces(address_raw)
        # filter short
        if len(address_val) < 5:
            address_val = None
            address_raw = None

    fields["address"] = {
        "value": address_val,
        "raw_value": address_raw,
        "normalized_value": address_val,
        "masked_value": None,
        "confidence": round(avg_conf*0.9,3) if address_val else 0.0,
        "confidence_basis": "OCR_ENGINE",
        "status": "DETECTED" if address_val else "NOT_FOUND",
        "sources": [{"type":"OCR","confidence": round(avg_conf*0.9,3)}] if address_val else [],
        "bounding_box": None,
        "page": 1,
        "notes": "Address extracted after label" if address_val else "No address label",
        "consistency": None
    }

    return fields
