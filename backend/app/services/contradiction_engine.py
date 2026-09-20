import re

def build_contradictions(evidence, qr_consistency, fields, offline_ekyc=None):
    contradictions = []
    cid_counter = 1
    def cid():
        nonlocal cid_counter
        c = f"C-AAD-{cid_counter:03d}"
        cid_counter+=1
        return c

    # From QR consistency mismatches
    if qr_consistency and qr_consistency.get("mismatches",0)>0:
        for item in qr_consistency.get("items",[]):
            if item["result"]=="MISMATCH":
                # find evidence ids related
                eids = [e["evidence_id"] for e in evidence if e["source"]=="CONSISTENCY" and item["field"] in e["finding"].lower()]
                contradictions.append({
                    "contradiction_id": cid(),
                    "field": item["field"],
                    "source_a": "OCR",
                    "value_a": item["printed_value"],
                    "source_b": "QR",
                    "value_b": item["qr_value"],
                    "severity": "HIGH" if item["field"] in ["dob","aadhaar_number"] else "MEDIUM",
                    "confidence": 0.85,
                    "description": f"Printed {item['field']} differs from QR {item['field']}",
                    "possible_explanations": ["OCR error due to image quality","QR decoding issue","Formatting difference","Genuine discrepancy requiring verification","Possible localized manipulation"],
                    "evidence_ids": eids or [e["evidence_id"] for e in evidence if "CONSISTENCY" in e["category"]][:2],
                    "group": "QR_CONSISTENCY"
                })

    # Check for multiple sources consistency (OCR, QR, eKYC)
    if offline_ekyc and offline_ekyc.get("provided") and offline_ekyc.get("status")=="PARSED":
        ekyc_fields = offline_ekyc.get("fields",{})
        # check name across three
        ocr_name = fields.get("name",{}).get("value")
        qr_name = None
        # find qr name from evidence? or directly from qr_consistency? Let's look up in evidence QR_FIELD
        for e in evidence:
            if e["source"]=="QR" and e["data"] and e["data"].get("field")=="name":
                qr_name = e["data"].get("value")
        ekyc_name = ekyc_fields.get("name")
        # if at least two present and mismatch
        values = {"OCR":ocr_name, "QR":qr_name, "EKYC":ekyc_name}
        present = {k:v for k,v in values.items() if v}
        if len(present)>=2:
            # normalize
            def norm(s): return re.sub(r"\s+"," ",s.lower().strip()) if s else ""
            norms = {k:norm(v) for k,v in present.items()}
            if len(set(norms.values()))>1:
                # contradiction between sources
                # pick two differing
                keys = list(present.keys())
                contradictions.append({
                    "contradiction_id": cid(),
                    "field": "name",
                    "source_a": keys[0],
                    "value_a": present[keys[0]],
                    "source_b": keys[1],
                    "value_b": present[keys[1]],
                    "severity": "HIGH",
                    "confidence": 0.9,
                    "description": f"Name differs between {keys[0]} and {keys[1]} (three-source check)",
                    "possible_explanations": ["OCR error","Data entry variation","Document inconsistency"],
                    "evidence_ids": [e["evidence_id"] for e in evidence if "name" in e["finding"].lower()][:3],
                    "group": "THREE_SOURCE"
                })

    # Biometric mismatch as contradiction? Face vs photo?
    # Could add forensic vs field: e.g., DOB anomaly + QR mismatch correlated
    # For grouping, we will handle via evidence_relations

    return contradictions

def build_evidence_relations(evidence, contradictions):
    relations = []
    # Group correlated evidence: OCR field extraction and number validation both derived from OCR image? But we marked independent_source differently.
    # Identify correlated groups
    rid=1
    # Group 1: All OCR-derived fields are correlated (not independent)
    ocr_eids = [e["evidence_id"] for e in evidence if e["source"]=="OCR"]
    if len(ocr_eids)>=2:
        relations.append({
            "relation_id": f"R-AAD-{rid:03d}",
            "type": "CORRELATED",
            "evidence_ids": ocr_eids,
            "description": "OCR-derived field extractions share the same image source and OCR engine; not independent evidence of authenticity."
        })
        rid+=1
    # Group 2: QR consistency evidences are derived from both OCR and QR - correlated with their sources?
    consistency_eids = [e["evidence_id"] for e in evidence if e["group"]=="CONSISTENCY"]
    if len(consistency_eids)>=2:
        relations.append({
            "relation_id": f"R-AAD-{rid:03d}",
            "type": "CORRELATED",
            "evidence_ids": consistency_eids,
            "description": "Multiple QR consistency checks share the same QR decoding event."
        })
        rid+=1
    # Group 3: Forensic regions may be correlated (same forensic method)
    forensic_eids = [e["evidence_id"] for e in evidence if e["group"]=="FORENSICS"]
    if len(forensic_eids)>=2:
        relations.append({
            "relation_id": f"R-AAD-{rid:03d}",
            "type": "CORRELATED",
            "evidence_ids": forensic_eids,
            "description": "Multiple forensic anomalies from overlapping analysis blocks may reflect the same region."
        })
        rid+=1
    # Independent sources: QR vs Forensics vs Biometric are independent
    independent_groups = []
    qr_eids = [e["evidence_id"] for e in evidence if e["group"]=="QR"]
    bio_eids = [e["evidence_id"] for e in evidence if e["group"]=="BIOMETRIC"]
    forensic_independent = [e["evidence_id"] for e in evidence if e["group"]=="FORENSICS"]
    # If we have evidence from QR inconsistency + forensic anomaly on same field (e.g., DOB), that's strong independent corroboration
    # We flag as independent
    if qr_eids and forensic_independent:
        relations.append({
            "relation_id": f"R-AAD-{rid:03d}",
            "type": "INDEPENDENT",
            "evidence_ids": qr_eids[:1] + forensic_independent[:1],
            "description": "QR and forensic evidence are independent sources; agreement increases confidence."
        })
        rid+=1

    return relations
