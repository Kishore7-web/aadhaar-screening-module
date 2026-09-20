import cv2
import numpy as np
import re
import time

def detect_and_decode_qr(images):
    start = time.time()
    detector = cv2.QRCodeDetector()
    qr_info = {
        "status": "QR_NOT_PRESENT",
        "decoded": False,
        "data_raw": None,
        "data_truncated": None,
        "fields": {},
        "bounding_box": None,
        "page": None,
        "decode_time_ms": None,
        "notes": None
    }
    # Try each image
    for item in images:
        img = item["image"]
        page = item["page"]
        try:
            # detect and decode
            data, bbox, straight_qrcode = detector.detectAndDecode(img)
            if bbox is not None and data:
                # success
                qr_info["status"] = "QR_PRESENT"
                qr_info["decoded"] = True
                qr_info["data_raw"] = data
                qr_info["data_truncated"] = data[:200] + ("..." if len(data)>200 else "")
                qr_info["fields"] = parse_qr_data(data)
                # bbox is 4 points
                if bbox is not None:
                    pts = bbox[0].astype(int)
                    x,y,w,h = cv2.boundingRect(pts)
                    qr_info["bounding_box"] = [int(x),int(y),int(w),int(h)]
                qr_info["page"] = page
                qr_info["notes"] = f"QR decoded from page {page}, length {len(data)}"
                break
            elif bbox is not None and not data:
                # detected but not decoded
                qr_info["status"] = "QR_UNREADABLE"
                qr_info["notes"] = "QR detected but could not be decoded."
                if bbox is not None:
                    try:
                        pts = bbox[0].astype(int)
                        x,y,w,h = cv2.boundingRect(pts)
                        qr_info["bounding_box"] = [int(x),int(y),int(w),int(h)]
                        qr_info["page"] = page
                    except:
                        pass
                # try multi?
                # Try detectMulti
                try:
                    retval, decoded_info, points, straight = detector.detectAndDecodeMulti(img)
                    if retval and decoded_info:
                        for d, p in zip(decoded_info, points):
                            if d:
                                qr_info["status"] = "QR_PRESENT"
                                qr_info["decoded"] = True
                                qr_info["data_raw"] = d
                                qr_info["data_truncated"] = d[:200]
                                qr_info["fields"] = parse_qr_data(d)
                                x,y,w,h = cv2.boundingRect(p.astype(int))
                                qr_info["bounding_box"] = [int(x),int(y),int(w),int(h)]
                                qr_info["page"] = page
                                qr_info["notes"] = "QR multi decoded"
                                break
                except:
                    pass
            else:
                # try detectMulti for scanned images with multiple QR
                try:
                    retval, decoded_info, points, straight = detector.detectAndDecodeMulti(img)
                    if retval:
                        for d, p in zip(decoded_info, points):
                            if d:
                                qr_info["status"] = "QR_PRESENT"
                                qr_info["decoded"] = True
                                qr_info["data_raw"] = d
                                qr_info["data_truncated"] = d[:200]
                                qr_info["fields"] = parse_qr_data(d)
                                x,y,w,h = cv2.boundingRect(p.astype(int))
                                qr_info["bounding_box"] = [int(x),int(y),int(w),int(h)]
                                qr_info["page"] = page
                                qr_info["notes"] = "QR multi decoded"
                                break
                except:
                    pass
        except Exception as e:
            qr_info["notes"] = f"QR detection error: {e}"
            continue

    qr_info["decode_time_ms"] = int((time.time()-start)*1000)
    if qr_info["status"] == "QR_NOT_PRESENT":
        qr_info["notes"] = "No QR code detected. Some Aadhaar variants may not contain a readable QR."

    return qr_info

def parse_qr_data(data: str):
    fields = {}
    if not data:
        return fields
    # Try to parse as XML-like or delimited? UIDAI secure QR is often compressed binary but we test text parsing
    # Heuristics:
    # If data contains xml tags: extract
    # If data is numeric delimited or vCard-like
    # We'll attempt multiple parsers

    # Attempt XML regex
    try:
        # Look for PrintLetterBarcodeData or similar
        # Example: <PrintLetterBarcodeData uid="1234..." name="ABC" yob="1990" gender="M" ... />
        import re
        # uid
        m = re.search(r'uid=["\']?(\d{12}|[Xx]{4}\s+[Xx]{4}\s+\d{4})["\']?', data)
        if m:
            fields["uid"] = m.group(1)
        m = re.search(r'name=["\']?([^"\']+)["\']?', data, re.IGNORECASE)
        if m:
            fields["name"] = m.group(1).strip()
        m = re.search(r'yob=["\']?(\d{4})["\']?', data, re.IGNORECASE)
        if m:
            fields["yob"] = m.group(1)
        m = re.search(r'dob=["\']?([^"\']+)["\']?', data, re.IGNORECASE)
        if m:
            fields["dob"] = m.group(1).strip()
        m = re.search(r'gender=["\']?([MFOTmfot])["\']?', data, re.IGNORECASE)
        if m:
            g = m.group(1).upper()
            fields["gender"] = {"M":"MALE","F":"FEMALE","T":"TRANSGENDER","O":"OTHER"}.get(g, g)
        m = re.search(r'co=["\']?([^"\']+)["\']?', data)
        if m:
            fields["co"] = m.group(1)
        m = re.search(r'house=["\']?([^"\']+)["\']?', data, re.IGNORECASE)
        if m:
            fields["house"] = m.group(1)
        m = re.search(r'street=["\']?([^"\']+)["\']?', data, re.IGNORECASE)
        if m:
            fields["street"] = m.group(1)
        m = re.search(r'vtc=["\']?([^"\']+)["\']?', data, re.IGNORECASE)
        if m:
            fields["vtc"] = m.group(1)
        m = re.search(r'dist=["\']?([^"\']+)["\']?', data, re.IGNORECASE)
        if m:
            fields["dist"] = m.group(1)
        m = re.search(r'state=["\']?([^"\']+)["\']?', data, re.IGNORECASE)
        if m:
            fields["state"] = m.group(1)
        m = re.search(r'pc=["\']?(\d{6})["\']?', data, re.IGNORECASE)
        if m:
            fields["pc"] = m.group(1)
        # If not xml, try pipe delimited ? UIDAI QR v2 may be: data like "123456789012|ABC|1990|M|..."
        if not fields:
            parts = re.split(r"[|\n]", data)
            if len(parts) >= 3:
                # heuristic: first part may be uid, second name, third dob/yob, fourth gender
                if re.match(r"\d{12}", parts[0]) or re.match(r"[Xx]{4}", parts[0]):
                    fields["uid"] = parts[0].strip()
                    if len(parts)>1:
                        fields["name"] = parts[1].strip()
                    if len(parts)>2:
                        # try dob
                        if re.match(r"\d{2}/\d{2}/\d{4}", parts[2]):
                            fields["dob"] = parts[2].strip()
                        elif re.match(r"\d{4}", parts[2]):
                            fields["yob"] = parts[2].strip()
                    if len(parts)>3:
                        g = parts[3].strip().upper()
                        if g in ["M","F","MALE","FEMALE"]:
                            fields["gender"] = g if len(g)>1 else ({"M":"MALE","F":"FEMALE"}.get(g,g))

        # If still empty, store raw truncation and attempt generic key=value parsing
        if not fields:
            # key=value lines
            kv = re.findall(r"(\w+)\s*[:=]\s*([^\n|,;]+)", data)
            for k,v in kv:
                kl = k.lower()
                if kl in ["name","dob","yob","gender","uid","aadhaar","address","pc","state"]:
                    fields[kl] = v.strip()[:100]
            if not fields:
                # store minimal
                fields["raw_preview"] = data[:500]
                fields["raw_length"] = len(data)
                fields["encoding"] = "unknown/possibly_compressed"

        # Add address composition if parts present
        if any(k in fields for k in ["house","street","vtc","dist","state","pc"]):
            addr_parts = []
            for k in ["house","street","vtc","dist","state","pc"]:
                if fields.get(k):
                    addr_parts.append(fields[k])
            fields["address_composed"] = ", ".join(addr_parts)

    except Exception as e:
        fields["parse_error"] = str(e)
        fields["raw_preview"] = data[:200]

    return fields

def compare_qr_printed(fields_ocr: dict, qr_fields: dict):
    items = []
    mismatches = 0
    # Normalize for comparison
    def norm(s):
        if not s:
            return ""
        return re.sub(r"\s+", " ", s.strip().lower())

    # Map OCR fields to QR fields
    mapping = [
        ("name", "name", "name"),
        ("dob", "dob", "dob"),
        ("gender", "gender", "gender"),
        # yob fallback for dob
        ("yob", "year_of_birth", "yob"),
    ]
    # Actually check each field that exists in both
    # Name
    ocr_name = fields_ocr.get("name", {}).get("value")
    qr_name = qr_fields.get("name")
    if ocr_name or qr_name:
        if ocr_name and qr_name:
            # Lenient name comparison: ignore spaces, case, and colon artifacts; handle OCR missing space (AaravKumar vs Aarav Kumar)
            def norm_name(s):
                return re.sub(r"[^a-z]", "", s.strip().lower())
            match = norm(ocr_name) == norm(qr_name) or norm_name(ocr_name) == norm_name(qr_name)
            # Also consider if one is substring of other with high overlap (ocr often merges)
            if not match:
                a = norm_name(ocr_name)
                b = norm_name(qr_name)
                # If one contains the other and length diff <2, consider match
                if (a in b or b in a) and abs(len(a)-len(b)) <=2:
                    match = True
            result = "MATCH" if match else "MISMATCH"
            if not match:
                mismatches+=1
            items.append({"field":"name","printed_value":ocr_name,"qr_value":qr_name,"result":result,"severity":"HIGH" if not match else "INFO","notes":None})
        else:
            items.append({"field":"name","printed_value":ocr_name,"qr_value":qr_name,"result":"NOT_AVAILABLE","severity":"INFO","notes":"Field not available in one source"})
    # DOB
    ocr_dob = fields_ocr.get("dob", {}).get("value") or fields_ocr.get("dob", {}).get("normalized_value")
    qr_dob = qr_fields.get("dob")
    qr_yob = qr_fields.get("yob")
    # if qr has yob and ocr has full dob, compare year
    if ocr_dob or qr_dob or qr_yob:
        qr_val = qr_dob or qr_yob
        if ocr_dob and qr_val:
            # compare normalized
            # if ocr dob is full date and qr_yob is year, compare year only
            ocr_year = None
            if ocr_dob:
                m = re.search(r"\d{4}", ocr_dob)
                if m:
                    ocr_year = m.group()
            qr_year = None
            if qr_val:
                m = re.search(r"\d{4}", qr_val)
                if m:
                    qr_year = m.group()
            # For full dob equality, we compare normalized lower
            if qr_dob and ocr_dob:
                # both have full dob candidate
                match = norm(ocr_dob) == norm(qr_dob)
                # also check year if full mismatch but year matches? then partial
                if not match and ocr_year and qr_year and ocr_year==qr_year:
                    # maybe formatting difference? still mismatch but note year matches
                    result = "MISMATCH"
                else:
                    result = "MATCH" if match else "MISMATCH"
            else:
                # compare years
                match = ocr_year == qr_year if ocr_year and qr_year else False
                result = "MATCH" if match else "MISMATCH"
            if result=="MISMATCH":
                mismatches+=1
            items.append({"field":"dob","printed_value":ocr_dob,"qr_value":qr_val,"result":result,"severity":"HIGH" if result=="MISMATCH" else "INFO","notes": None})
        else:
            items.append({"field":"dob","printed_value":ocr_dob,"qr_value":qr_val,"result":"NOT_AVAILABLE","severity":"INFO","notes":None})

    # Gender
    ocr_gender = fields_ocr.get("gender", {}).get("value")
    qr_gender = qr_fields.get("gender")
    if ocr_gender or qr_gender:
        if ocr_gender and qr_gender:
            # normalize: MALE vs M vs F
            def norm_g(s):
                s = s.strip().upper()
                if s in ["M","MALE"]:
                    return "MALE"
                if s in ["F","FEMALE"]:
                    return "FEMALE"
                return s
            match = norm_g(ocr_gender) == norm_g(qr_gender)
            result = "MATCH" if match else "MISMATCH"
            if not match:
                mismatches+=1
            items.append({"field":"gender","printed_value":ocr_gender,"qr_value":qr_gender,"result":result,"severity":"MEDIUM" if not match else "INFO","notes":None})
        else:
            items.append({"field":"gender","printed_value":ocr_gender,"qr_value":qr_gender,"result":"NOT_AVAILABLE","severity":"INFO","notes":None})

    # Aadhaar number (masked vs full)
    ocr_aadhaar = fields_ocr.get("aadhaar_number", {}).get("value")
    qr_uid = qr_fields.get("uid")
    if ocr_aadhaar or qr_uid:
        if ocr_aadhaar and qr_uid:
            # if ocr is masked (XXXX XXXX 1234) and qr is full, compare last 4
            ocr_digits = re.sub(r"\D","",ocr_aadhaar)
            qr_digits = re.sub(r"\D","",qr_uid) if qr_uid else ""
            if "XXXX" in ocr_aadhaar or "xxxx" in ocr_aadhaar.lower():
                # masked: compare last 4
                match = ocr_digits[-4:] == qr_digits[-4:] if len(ocr_digits)>=4 and len(qr_digits)>=4 else False
                # if masked last 4 matches full's last 4, it's MATCH
                result = "MATCH" if match else "MISMATCH"
            else:
                # both full? compare full
                # normalize remove spaces
                match = ocr_digits == qr_digits
                result = "MATCH" if match else "MISMATCH"
            if result=="MISMATCH":
                mismatches+=1
            items.append({"field":"aadhaar_number","printed_value":ocr_aadhaar,"qr_value":qr_uid,"result":result,"severity":"HIGH" if result=="MISMATCH" else "INFO","notes":None})
        else:
            items.append({"field":"aadhaar_number","printed_value":ocr_aadhaar,"qr_value":qr_uid,"result":"NOT_AVAILABLE","severity":"INFO","notes":None})

    overall = "MATCH" if mismatches==0 and any(i["result"]=="MATCH" for i in items) else ("MISMATCH" if mismatches>0 else "NOT_CHECKED")

    return {"checked": len(items)>0, "items": items, "overall": overall, "mismatches": mismatches}
