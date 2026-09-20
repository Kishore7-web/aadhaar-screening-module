from typing import List, Dict, Any

def build_evidence(
    fields: dict,
    number_validation: dict,
    qr_info: dict,
    qr_consistency: dict,
    photo_info: dict,
    biometric: dict,
    forensics: dict,
    metadata: dict,
    doc_identification: dict,
    quality: dict,
    offline_ekyc: dict
):
    evidence = []
    eid_counter = 1
    def eid():
        nonlocal eid_counter
        eid_str = f"E-AAD-{eid_counter:03d}"
        eid_counter+=1
        return eid_str

    # FIELD EXTRACTION
    if fields.get("name", {}).get("status")=="DETECTED":
        evidence.append({
            "evidence_id": eid(),
            "source": "OCR",
            "category": "FIELD_EXTRACTION",
            "finding": f"Name extracted as '{fields['name']['value']}'",
            "severity": "INFO",
            "confidence": fields["name"]["confidence"],
            "confidence_basis": fields["name"]["confidence_basis"],
            "group": "FIELD",
            "independent_source": False, # OCR derived
            "region": None,
            "artifact": None,
            "data": {"field":"name","value":fields["name"]["value"]}
        })
    if fields.get("dob", {}).get("status")=="DETECTED":
        evidence.append({
            "evidence_id": eid(),
            "source": "OCR",
            "category": "FIELD_EXTRACTION",
            "finding": f"DOB extracted as {fields['dob']['value']} (normalized {fields['dob']['normalized_value']})",
            "severity": "INFO",
            "confidence": fields["dob"]["confidence"],
            "confidence_basis": fields["dob"]["confidence_basis"],
            "group": "FIELD",
            "independent_source": False,
            "region": None,
            "artifact": None,
            "data": {"field":"dob","value":fields["dob"]["value"]}
        })
    if fields.get("gender", {}).get("status")=="DETECTED":
        evidence.append({
            "evidence_id": eid(),
            "source": "OCR",
            "category": "FIELD_EXTRACTION",
            "finding": f"Gender extracted as '{fields['gender']['value']}'",
            "severity": "INFO",
            "confidence": fields["gender"]["confidence"],
            "confidence_basis": fields["gender"]["confidence_basis"],
            "group": "FIELD",
            "independent_source": False,
            "region": None,
            "artifact": None,
            "data": {"field":"gender","value":fields["gender"]["value"]}
        })
    if fields.get("address", {}).get("status")=="DETECTED":
        evidence.append({
            "evidence_id": eid(),
            "source": "OCR",
            "category": "FIELD_EXTRACTION",
            "finding": f"Address extracted ({len(fields['address']['value'])} chars)",
            "severity": "INFO",
            "confidence": fields["address"]["confidence"],
            "confidence_basis": fields["address"]["confidence_basis"],
            "group": "FIELD",
            "independent_source": False,
            "region": None,
            "artifact": None,
            "data": {"field":"address","value":fields["address"]["value"][:80]}
        })
    if fields.get("aadhaar_number", {}).get("status") in ["DETECTED","MASKED"]:
        val = fields["aadhaar_number"]["value"]
        masked_note = " (masked)" if fields["aadhaar_number"]["status"]=="MASKED" else ""
        evidence.append({
            "evidence_id": eid(),
            "source": "OCR",
            "category": "NUMBER_EXTRACTION",
            "finding": f"Aadhaar number candidate extracted{masked_note}: {val}",
            "severity": "INFO",
            "confidence": fields["aadhaar_number"]["confidence"],
            "confidence_basis": fields["aadhaar_number"]["confidence_basis"],
            "group": "NUMBER",
            "independent_source": False,
            "region": None,
            "artifact": None,
            "data": {"field":"aadhaar_number","value":val, "status":fields["aadhaar_number"]["status"]}
        })

    # NUMBER VALIDATION
    if number_validation:
        fmt = number_validation.get("format_status")
        chk = number_validation.get("checksum_status")
        if fmt == "FORMAT_VALID" and chk == "CHECKSUM_VALID":
            evidence.append({
                "evidence_id": eid(),
                "source": "NUMBER_VALIDATION",
                "category": "CHECKSUM",
                "finding": "Mathematical/checksum validation passed for Aadhaar number.",
                "severity": "INFO",
                "confidence": 1.0,
                "confidence_basis": "DETERMINISTIC",
                "group": "NUMBER",
                "independent_source": True, # deterministic check independent from OCR?
                "region": None,
                "artifact": None,
                "data": {"format":fmt,"checksum":chk}
            })
        elif chk == "CHECKSUM_INVALID":
            evidence.append({
                "evidence_id": eid(),
                "source": "NUMBER_VALIDATION",
                "category": "CHECKSUM",
                "finding": f"Checksum invalid for candidate {number_validation.get('masked_value')}. Possible transcription error.",
                "severity": "HIGH",
                "confidence": 1.0,
                "confidence_basis": "DETERMINISTIC",
                "group": "NUMBER",
                "independent_source": True,
                "region": None,
                "artifact": None,
                "data": {"format":fmt,"checksum":chk}
            })
        elif fmt == "MASKED":
            evidence.append({
                "evidence_id": eid(),
                "source": "NUMBER_VALIDATION",
                "category": "MASKED",
                "finding": "Masked Aadhaar detected. Full checksum not checked.",
                "severity": "INFO",
                "confidence": 1.0,
                "confidence_basis": "DETERMINISTIC",
                "group": "NUMBER",
                "independent_source": True,
                "region": None,
                "artifact": None,
                "data": {"format":fmt}
            })
        elif fmt == "FORMAT_INVALID":
            evidence.append({
                "evidence_id": eid(),
                "source": "NUMBER_VALIDATION",
                "category": "FORMAT",
                "finding": f"Format invalid: {number_validation.get('checksum_message')}",
                "severity": "MEDIUM",
                "confidence": 1.0,
                "confidence_basis": "DETERMINISTIC",
                "group": "NUMBER",
                "independent_source": True,
                "region": None,
                "artifact": None,
                "data": {"format":fmt}
            })

    # QR
    if qr_info.get("status")=="QR_PRESENT" and qr_info.get("decoded"):
        evidence.append({
            "evidence_id": eid(),
            "source": "QR",
            "category": "QR",
            "finding": f"QR code decoded, {len(qr_info.get('fields',{}))} fields parsed.",
            "severity": "INFO",
            "confidence": 1.0,
            "confidence_basis": "DETERMINISTIC",
            "group": "QR",
            "independent_source": True,
            "region": None,
            "artifact": None,
            "data": {"fields": list(qr_info.get("fields",{}).keys())}
        })
        # QR fields parsed
        for k,v in qr_info.get("fields",{}).items():
            if k in ["name","dob","gender","uid"]:
                evidence.append({
                    "evidence_id": eid(),
                    "source": "QR",
                    "category": "QR_FIELD",
                    "finding": f"QR field {k}: {str(v)[:50]}",
                    "severity": "INFO",
                    "confidence": 1.0,
                    "confidence_basis": "DETERMINISTIC",
                    "group": "QR",
                    "independent_source": True,
                    "region": None,
                    "artifact": None,
                    "data": {"field":k,"value":v}
                })
    elif qr_info.get("status")=="QR_NOT_PRESENT":
        evidence.append({
            "evidence_id": eid(),
            "source": "QR",
            "category": "QR",
            "finding": "No QR code detected in document.",
            "severity": "INFO",
            "confidence": 1.0,
            "confidence_basis": "HEURISTIC",
            "group": "QR",
            "independent_source": True,
            "region": None,
            "artifact": None,
            "data": {}
        })
    elif qr_info.get("status")=="QR_UNREADABLE":
        evidence.append({
            "evidence_id": eid(),
            "source": "QR",
            "category": "QR",
            "finding": "QR detected but could not be decoded.",
            "severity": "LOW",
            "confidence": 0.7,
            "confidence_basis": "HEURISTIC",
            "group": "QR",
            "independent_source": True,
            "region": None,
            "artifact": None,
            "data": {}
        })

    # QR consistency
    if qr_consistency and qr_consistency.get("checked"):
        for item in qr_consistency.get("items",[]):
            if item["result"]=="MISMATCH":
                evidence.append({
                    "evidence_id": eid(),
                    "source": "CONSISTENCY",
                    "category": "CONTRADICTION",
                    "finding": f"Printed {item['field']} ('{item['printed_value']}') differs from QR {item['field']} ('{item['qr_value']}')",
                    "severity": "HIGH" if item["field"] in ["dob","aadhaar_number","name"] else "MEDIUM",
                    "confidence": 0.85,
                    "confidence_basis": "HEURISTIC",
                    "group": "CONSISTENCY",
                    "independent_source": True,
                    "region": None,
                    "artifact": None,
                    "data": item
                })
            elif item["result"]=="MATCH":
                evidence.append({
                    "evidence_id": eid(),
                    "source": "CONSISTENCY",
                    "category": "CONSISTENCY",
                    "finding": f"Printed {item['field']} matches QR {item['field']}.",
                    "severity": "INFO",
                    "confidence": 0.9,
                    "confidence_basis": "HEURISTIC",
                    "group": "CONSISTENCY",
                    "independent_source": True,
                    "region": None,
                    "artifact": None,
                    "data": item
                })

    # Photo
    if photo_info.get("status")=="DETECTED":
        evidence.append({
            "evidence_id": eid(),
            "source": "PHOTO",
            "category": "PHOTO",
            "finding": f"Document photograph detected (quality {photo_info.get('quality_label')})",
            "severity": "INFO",
            "confidence": photo_info.get("quality_score",50)/100 if photo_info.get("quality_score") else 0.6,
            "confidence_basis": "HEURISTIC",
            "group": "PHOTO",
            "independent_source": True,
            "region": None,
            "artifact": None,
            "data": {"bbox": photo_info.get("bounding_box"), "quality": photo_info.get("quality_label")}
        })
    elif photo_info.get("status")=="LOW_QUALITY":
        evidence.append({
            "evidence_id": eid(),
            "source": "PHOTO",
            "category": "PHOTO_QUALITY",
            "finding": "Document photograph detected but low quality.",
            "severity": "LOW",
            "confidence": 0.6,
            "confidence_basis": "HEURISTIC",
            "group": "PHOTO",
            "independent_source": True,
            "region": None,
            "artifact": None,
            "data": {}
        })
    elif photo_info.get("status")=="NOT_FOUND":
        evidence.append({
            "evidence_id": eid(),
            "source": "PHOTO",
            "category": "PHOTO",
            "finding": "No document photograph/face detected.",
            "severity": "MEDIUM",
            "confidence": 0.7,
            "confidence_basis": "HEURISTIC",
            "group": "PHOTO",
            "independent_source": True,
            "region": None,
            "artifact": None,
            "data": {}
        })

    # Biometric
    if biometric.get("status")=="MATCH":
        evidence.append({
            "evidence_id": eid(),
            "source": "BIOMETRIC",
            "category": "FACE_COMPARISON",
            "finding": f"Face comparison consistent (similarity {biometric.get('similarity')}, threshold {biometric.get('threshold')})",
            "severity": "INFO",
            "confidence": biometric.get("similarity"),
            "confidence_basis": "MODEL",
            "group": "BIOMETRIC",
            "independent_source": True,
            "region": None,
            "artifact": None,
            "data": {"similarity": biometric.get("similarity"), "threshold": biometric.get("threshold")}
        })
    elif biometric.get("status")=="MISMATCH":
        evidence.append({
            "evidence_id": eid(),
            "source": "BIOMETRIC",
            "category": "FACE_COMPARISON",
            "finding": f"Face comparison not consistent (similarity {biometric.get('similarity')})",
            "severity": "HIGH",
            "confidence": biometric.get("similarity"),
            "confidence_basis": "MODEL",
            "group": "BIOMETRIC",
            "independent_source": True,
            "region": None,
            "artifact": None,
            "data": {"similarity": biometric.get("similarity")}
        })
    elif biometric.get("status")=="LOW_CONFIDENCE":
        evidence.append({
            "evidence_id": eid(),
            "source": "BIOMETRIC",
            "category": "FACE_COMPARISON",
            "finding": "Face comparison inconclusive due to quality/pose.",
            "severity": "LOW",
            "confidence": biometric.get("similarity"),
            "confidence_basis": "MODEL",
            "group": "BIOMETRIC",
            "independent_source": True,
            "region": None,
            "artifact": None,
            "data": biometric
        })

    # Forensics
    if forensics.get("analyzed"):
        if forensics.get("overall_label")=="SUSPICIOUS" and forensics.get("regions"):
            for region in forensics.get("regions",[]):
                evidence.append({
                    "evidence_id": region.get("evidence_id") or eid(),
                    "source": "FORENSICS",
                    "category": "IMAGE_MANIPULATION",
                    "finding": f"Localized forensic anomaly detected: {region.get('reason')} (method {region.get('method')})",
                    "severity": region.get("severity", "MEDIUM"),
                    "confidence": region.get("confidence",0.6),
                    "confidence_basis": region.get("confidence_basis","HEURISTIC"),
                    "group": "FORENSICS",
                    "independent_source": True,
                    "region": str(region.get("bounding_box")),
                    "artifact": region.get("region_id"),
                    "data": region
                })
        elif forensics.get("signals"):
            # Signals without localized regions are weak heuristics -> treat as INFO to avoid false REVIEW for clean docs
            # Only flag as LOW if signal is strong/repeated
            for sig in forensics.get("signals",[])[:1]:
                evidence.append({
                    "evidence_id": eid(),
                    "source": "FORENSICS",
                    "category": "FORENSIC_SIGNAL",
                    "finding": sig,
                    "severity": "INFO",
                    "confidence": 0.6,
                    "confidence_basis": "HEURISTIC",
                    "group": "FORENSICS",
                    "independent_source": True,
                    "region": None,
                    "artifact": None,
                    "data": {}
                })
        else:
            evidence.append({
                "evidence_id": eid(),
                "source": "FORENSICS",
                "category": "FORENSICS",
                "finding": "No significant forensic manipulation signal detected.",
                "severity": "INFO",
                "confidence": 0.6,
                "confidence_basis": "HEURISTIC",
                "group": "FORENSICS",
                "independent_source": True,
                "region": None,
                "artifact": None,
                "data": {}
            })

    # Metadata
    if metadata.get("editing_software_detected"):
        evidence.append({
            "evidence_id": eid(),
            "source": "METADATA",
            "category": "METADATA",
            "finding": "Editing software metadata detected.",
            "severity": "LOW",
            "confidence": 0.8,
            "confidence_basis": "HEURISTIC",
            "group": "METADATA",
            "independent_source": True,
            "region": None,
            "artifact": None,
            "data": {"software": metadata.get("software_tags")[:2] if metadata.get("software_tags") else []}
        })

    # Quality
    if quality.get("is_low_quality") or quality.get("is_blurry"):
        evidence.append({
            "evidence_id": eid(),
            "source": "QUALITY",
            "category": "IMAGE_QUALITY",
            "finding": f"Image quality low (blur score {quality.get('blur_score'):.1f}, label {quality.get('overall_label')})",
            "severity": "MEDIUM",
            "confidence": 0.8,
            "confidence_basis": "HEURISTIC",
            "group": "QUALITY",
            "independent_source": True,
            "region": None,
            "artifact": None,
            "data": quality
        })
    else:
        if quality.get("overall_score") is not None:
            evidence.append({
                "evidence_id": eid(),
                "source": "QUALITY",
                "category": "IMAGE_QUALITY",
                "finding": f"Image quality assessed as {quality.get('overall_label')} (score {quality.get('overall_score')})",
                "severity": "INFO",
                "confidence": 0.7,
                "confidence_basis": "HEURISTIC",
                "group": "QUALITY",
                "independent_source": True,
                "region": None,
                "artifact": None,
                "data": quality
            })

    # Document identification
    if doc_identification.get("result")=="UNSUPPORTED_DOCUMENT":
        evidence.append({
            "evidence_id": eid(),
            "source": "DOCUMENT_IDENTIFICATION",
            "category": "DOCUMENT_TYPE",
            "finding": "Document does not appear to be Aadhaar (insufficient signals).",
            "severity": "HIGH",
            "confidence": doc_identification.get("confidence"),
            "confidence_basis": "HEURISTIC",
            "group": "IDENTIFICATION",
            "independent_source": True,
            "region": None,
            "artifact": None,
            "data": doc_identification
        })
    elif doc_identification.get("result")=="NOT_CONFIDENT":
        evidence.append({
            "evidence_id": eid(),
            "source": "DOCUMENT_IDENTIFICATION",
            "category": "DOCUMENT_TYPE",
            "finding": "Document identification not confident - limited Aadhaar signals.",
            "severity": "LOW",
            "confidence": doc_identification.get("confidence"),
            "confidence_basis": "HEURISTIC",
            "group": "IDENTIFICATION",
            "independent_source": True,
            "region": None,
            "artifact": None,
            "data": doc_identification
        })

    # Offline eKYC consistency if provided
    if offline_ekyc and offline_ekyc.get("provided") and offline_ekyc.get("status")=="PARSED":
        ekyc_fields = offline_ekyc.get("fields",{})
        # Compare with OCR
        # For simplicity, evidence for eKYC parsed
        evidence.append({
            "evidence_id": eid(),
            "source": "EKYC",
            "category": "EKYC",
            "finding": f"Offline eKYC parsed with {len(ekyc_fields)} fields.",
            "severity": "INFO",
            "confidence": 1.0,
            "confidence_basis": "DETERMINISTIC",
            "group": "EKYC",
            "independent_source": True,
            "region": None,
            "artifact": None,
            "data": ekyc_fields
        })
        # Check consistency with OCR fields if possible
        # e.g., name mismatch
        if ekyc_fields.get("name") and fields.get("name",{}).get("value"):
            import re
            def norm(s): return re.sub(r"\s+"," ",s.lower().strip())
            if norm(ekyc_fields["name"]) != norm(fields["name"]["value"]):
                evidence.append({
                    "evidence_id": eid(),
                    "source": "CONSISTENCY",
                    "category": "EKYC_CONTRADICTION",
                    "finding": f"eKYC name '{ekyc_fields['name']}' differs from OCR name '{fields['name']['value']}'",
                    "severity": "HIGH",
                    "confidence": 0.85,
                    "confidence_basis": "HEURISTIC",
                    "group": "CONSISTENCY",
                    "independent_source": True,
                    "region": None,
                    "artifact": None,
                    "data": {"field":"name","ekyc":ekyc_fields["name"],"ocr":fields["name"]["value"]}
                })

    # Ensure evidence IDs unique and sorted? Keep order

    return evidence
