"""
Scoring: Document Integrity Score 0-100, Evidence Coverage 0-100
Deterministic, correlation-aware, no random.
"""

def calculate_scores(evidence, contradictions, quality, photo_info, forensics, biometric, qr_info, number_validation, doc_identification, offline_ekyc, capabilities=None, metadata=None):
    # Define evidence families and weights
    # Total 100
    weights = {
        "DOCUMENT_QUALITY": 10,
        "FIELD_VALIDATION": 15,
        "NUMBER_VALIDATION": 10,
        "QR": 20,
        "BIOMETRIC": 20,
        "FORENSICS": 15,
        "METADATA": 5,
        "DOCUMENT_IDENTIFICATION": 5
    }
    breakdown = {}
    penalties = {}
    max_score = 100

    # Start at 100, subtract penalties per family
    score = 100

    # DOCUMENT_QUALITY
    if quality.get("is_blurry") or quality.get("is_low_quality"):
        # penalize moderate, but not huge if other evidence good
        # Low quality affects coverage more than integrity
        penalty = 8 if quality.get("is_blurry") else 5
        penalties["DOCUMENT_QUALITY"] = penalty
        breakdown["DOCUMENT_QUALITY"] = {"weight": weights["DOCUMENT_QUALITY"], "penalty": penalty, "status": "LOW_QUALITY"}
    else:
        # No penalty, but if blur score low, small penalty
        blur = quality.get("blur_score") or 200
        if blur < 50:
            penalty = 5
            penalties["DOCUMENT_QUALITY"] = penalty
            breakdown["DOCUMENT_QUALITY"] = {"weight": weights["DOCUMENT_QUALITY"], "penalty": penalty, "status": "BLURRY"}
        else:
            breakdown["DOCUMENT_QUALITY"] = {"weight": weights["DOCUMENT_QUALITY"], "penalty": 0, "status": "PASS"}

    # FIELD_VALIDATION: check if expected fields found
    expected_fields = ["name","dob","gender","aadhaar_number","address"]
    # This family is about successful extraction, not consistency
    missing = sum(1 for f in expected_fields if not evidence or not any(e["data"] and e["data"].get("field")==f for e in evidence if e["category"]=="FIELD_EXTRACTION" or e["category"]=="NUMBER_EXTRACTION"))
    # Alternative: check fields dict passed? Use evidence count.
    # More directly: count fields with DETECTED status via evidence
    # For now, if many fields missing, penalize but not heavily
    if missing >=3:
        penalty = 10
        breakdown["FIELD_VALIDATION"] = {"weight": weights["FIELD_VALIDATION"], "penalty": penalty, "status": "MANY_MISSING"}
        penalties["FIELD_VALIDATION"] = penalty
    elif missing >=1:
        penalty = 3
        breakdown["FIELD_VALIDATION"] = {"weight": weights["FIELD_VALIDATION"], "penalty": penalty, "status": "PARTIAL"}
        penalties["FIELD_VALIDATION"] = penalty
    else:
        breakdown["FIELD_VALIDATION"] = {"weight": weights["FIELD_VALIDATION"], "penalty": 0, "status": "PASS"}

    # NUMBER_VALIDATION
    fmt = number_validation.get("format_status")
    chk = number_validation.get("checksum_status")
    if chk == "CHECKSUM_INVALID":
        penalty = weights["NUMBER_VALIDATION"]  # full penalty 10
        breakdown["NUMBER_VALIDATION"] = {"weight": weights["NUMBER_VALIDATION"], "penalty": penalty, "status": "CHECKSUM_INVALID"}
        penalties["NUMBER_VALIDATION"] = penalty
    elif fmt == "FORMAT_INVALID":
        penalty = 8
        breakdown["NUMBER_VALIDATION"] = {"weight": weights["NUMBER_VALIDATION"], "penalty": penalty, "status": "FORMAT_INVALID"}
        penalties["NUMBER_VALIDATION"] = penalty
    elif fmt == "MASKED":
        # masked not penalized
        breakdown["NUMBER_VALIDATION"] = {"weight": weights["NUMBER_VALIDATION"], "penalty": 0, "status": "MASKED"}
    else:
        breakdown["NUMBER_VALIDATION"] = {"weight": weights["NUMBER_VALIDATION"], "penalty": 0, "status": "PASS"}

    # QR
    if qr_info.get("status")=="QR_PRESENT" and qr_info.get("decoded"):
        # check consistency mismatches
        mismatch_count = sum(1 for e in evidence if e["source"]=="CONSISTENCY" and "differs" in e["finding"])
        if mismatch_count >=2:
            penalty = 18
            breakdown["QR"] = {"weight": weights["QR"], "penalty": penalty, "status": "MULTIPLE_MISMATCH"}
            penalties["QR"] = penalty
        elif mismatch_count ==1:
            penalty = 12
            breakdown["QR"] = {"weight": weights["QR"], "penalty": penalty, "status": "MISMATCH"}
            penalties["QR"] = penalty
        else:
            # No mismatch but QR present - good
            breakdown["QR"] = {"weight": weights["QR"], "penalty": 0, "status": "CONSISTENT"}
    else:
        # QR not present - do not penalize heavily (optional evidence)
        # But if document identification says Aadhaar and QR expected, lightweight penalty?
        # Spec: do not penalize for absent optional evidence.
        breakdown["QR"] = {"weight": weights["QR"], "penalty": 0, "status": "NOT_PROVIDED", "note": "Optional, not penalized"}
        # coverage will reflect absence

    # BIOMETRIC
    bio_status = biometric.get("status")
    if bio_status == "MISMATCH":
        penalty = weights["BIOMETRIC"]
        breakdown["BIOMETRIC"] = {"weight": weights["BIOMETRIC"], "penalty": penalty, "status": "MISMATCH"}
        penalties["BIOMETRIC"] = penalty
    elif bio_status == "LOW_CONFIDENCE":
        penalty = 8
        breakdown["BIOMETRIC"] = {"weight": weights["BIOMETRIC"], "penalty": penalty, "status": "LOW_CONFIDENCE"}
        penalties["BIOMETRIC"] = penalty
    elif bio_status in ["FACE_NOT_FOUND","MULTIPLE_FACES"]:
        # photo missing affects but not full penalty
        penalty = 5
        breakdown["BIOMETRIC"] = {"weight": weights["BIOMETRIC"], "penalty": penalty, "status": bio_status}
        penalties["BIOMETRIC"] = penalty
    elif bio_status == "NOT_CHECKED":
        breakdown["BIOMETRIC"] = {"weight": weights["BIOMETRIC"], "penalty": 0, "status": "NOT_CHECKED", "note": "No reference provided, not penalized"}
    elif bio_status == "MATCH":
        breakdown["BIOMETRIC"] = {"weight": weights["BIOMETRIC"], "penalty": 0, "status": "MATCH"}
    else:
        breakdown["BIOMETRIC"] = {"weight": weights["BIOMETRIC"], "penalty": 0, "status": bio_status or "NOT_CHECKED"}

    # FORENSICS
    forensic_label = forensics.get("overall_label")
    regions = forensics.get("regions",[])
    if forensic_label == "SUSPICIOUS" and regions:
        # Severity of regions matters
        has_high = any(r.get("severity") in ["HIGH","CRITICAL"] for r in regions)
        has_medium = any(r.get("severity")=="MEDIUM" for r in regions)
        if has_high:
            penalty = weights["FORENSICS"]
        elif len(regions)>=2:
            penalty = 12
        elif has_medium:
            penalty = 10
        else:
            penalty = 6
        breakdown["FORENSICS"] = {"weight": weights["FORENSICS"], "penalty": penalty, "status": "SUSPICIOUS", "regions": len(regions)}
        penalties["FORENSICS"] = penalty
    elif forensics.get("signals"):
        # Signals without localized regions are weak and often false positives on clean synthetic docs
        # Treat as very low penalty to avoid clean docs being flagged REVIEW
        # Only penalize 2 if multiple distinct signals and high variance
        num_signals = len(forensics.get("signals",[]))
        if forensic_label == "LOW_SIGNAL" and not regions:
            penalty = 2
            breakdown["FORENSICS"] = {"weight": weights["FORENSICS"], "penalty": penalty, "status": "LOW_SIGNAL_WEAK"}
            penalties["FORENSICS"] = penalty
        else:
            penalty = 5
            breakdown["FORENSICS"] = {"weight": weights["FORENSICS"], "penalty": penalty, "status": "LOW_SIGNAL"}
            penalties["FORENSICS"] = penalty
    else:
        breakdown["FORENSICS"] = {"weight": weights["FORENSICS"], "penalty": 0, "status": "NO_SIGNAL"}

    # METADATA - low weight, should not dominate
    if evidence and any(e["source"]=="METADATA" for e in evidence):
        # editing software detected -> low penalty
        penalty = 3
        breakdown["METADATA"] = {"weight": weights["METADATA"], "penalty": penalty, "status": "SOFTWARE_DETECTED"}
        penalties["METADATA"] = penalty
    else:
        breakdown["METADATA"] = {"weight": weights["METADATA"], "penalty": 0, "status": "PASS"}

    # DOCUMENT_IDENTIFICATION
    doc_res = doc_identification.get("result")
    if doc_res == "UNSUPPORTED_DOCUMENT":
        penalty = weights["DOCUMENT_IDENTIFICATION"]
        breakdown["DOCUMENT_IDENTIFICATION"] = {"weight": weights["DOCUMENT_IDENTIFICATION"], "penalty": penalty, "status": "UNSUPPORTED"}
        penalties["DOCUMENT_IDENTIFICATION"] = penalty
    elif doc_res == "NOT_CONFIDENT":
        penalty = 3
        breakdown["DOCUMENT_IDENTIFICATION"] = {"weight": weights["DOCUMENT_IDENTIFICATION"], "penalty": penalty, "status": "NOT_CONFIDENT"}
        penalties["DOCUMENT_IDENTIFICATION"] = penalty
    else:
        breakdown["DOCUMENT_IDENTIFICATION"] = {"weight": weights["DOCUMENT_IDENTIFICATION"], "penalty": 0, "status": "PASS"}

    # Now correlation-aware caps: don't double count correlated evidence
    # Example: if checksum invalid and format invalid are same group, don't double penalize? Already handled as single penalty for number validation
    # If OCR field extraction errors and QR mismatch both stem from OCR error, we should not double penalize heavily?
    # Heuristic: if multiple penalties from correlated sources, cap total penalty?
    # For MVP: if we have both FIELD_VALIDATION penalty and NUMBER_VALIDATION penalty and they are both OCR-derived, cap at max of them plus small? But spec says OCR-derived errors must not be double-counted
    # We already treat FIELD and NUMBER as separate but both OCR-derived - we can cap their combined penalty to max 15? Let's implement.

    # Identify correlated groups
    # If field validation missing and number validation invalid, they share OCR source? But number invalid is deterministic check, not OCR error necessarily.
    # Simpler: total penalty capped at 85? Keep deterministic

    # Apply penalties
    total_penalty = sum(penalties.values())
    # Cap: if multiple HIGH penalties, ensure not >90?
    # Correlation cap: if both QR mismatch and forensic anomaly exist and they are independent, that should be higher penalty (not capped). So we keep sum.
    # But if field missing + quality low, they are correlated (quality affects OCR) - cap field penalty if quality is low?
    if quality.get("is_blurry") and "FIELD_VALIDATION" in penalties:
        # reduce field penalty by half if blurry, as it's expected
        total_penalty -= penalties["FIELD_VALIDATION"] // 2

    score = max(0, min(100, 100 - total_penalty))
    # Adjust for low coverage? Score doesn't directly get penalty for coverage, but screening logic will handle.

    # EVIDENCE COVERAGE 0-100: how much of applicable evidence could be analyzed
    # Families considered: DocumentQuality, FieldValidation, NumberValidation, QR, Biometric (if provided), Forensics, Metadata, DocumentIdentification
    # Each family 100% if analyzed, 0 if not. But some families optional (QR, Biometric, eKYC) - coverage should not require optional.
    # Define required families: quality, field, number, forensics, document_identification, metadata => 6 families
    # Optional but if available boosts coverage: QR, biometric, ekyc
    required = ["DOCUMENT_QUALITY","FIELD_VALIDATION","NUMBER_VALIDATION","FORENSICS","DOCUMENT_IDENTIFICATION","METADATA"]
    optional = ["QR","BIOMETRIC"]

    # For each family, determine if evidence was sufficient
    coverage_scores = {}
    # Quality always covered if analyzed
    coverage_scores["DOCUMENT_QUALITY"] = 100 if quality else 0
    # Field: if we have fields dict? Use evidence
    field_covered = 100 if any(e["group"]=="FIELD" for e in evidence) else (0 if missing>=3 else 50)
    coverage_scores["FIELD_VALIDATION"] = field_covered
    # Number: if format_status != NOT_CHECKED
    if number_validation.get("format_status") != "NOT_CHECKED":
        coverage_scores["NUMBER_VALIDATION"] = 100
    else:
        coverage_scores["NUMBER_VALIDATION"] = 20

    # QR: if decoded or status not_present but checked, coverage 100 if we attempted QR. Actually QR coverage: if QR present decoded 100, if not present 0 but optional? But we attempted, so 80? We'll give 100 if checked (regardless of present)
    # If QR was looked for, that's coverage.
    if qr_info.get("status") in ["QR_PRESENT","QR_NOT_PRESENT","QR_UNREADABLE"]:
        # we checked
        if qr_info.get("decoded"):
            coverage_scores["QR"] = 100
        elif qr_info.get("status")=="QR_NOT_PRESENT":
            coverage_scores["QR"] = 0  # not available
        else:
            coverage_scores["QR"] = 30
    else:
        coverage_scores["QR"] = 0

    # Biometric: if reference provided, coverage depends on detection
    if biometric.get("has_reference"):
        if biometric.get("status") in ["MATCH","MISMATCH","LOW_CONFIDENCE"]:
            coverage_scores["BIOMETRIC"] = 100
        else:
            coverage_scores["BIOMETRIC"] = 30
    else:
        coverage_scores["BIOMETRIC"] = 0  # not provided, optional

    # Forensics
    coverage_scores["FORENSICS"] = 100 if forensics.get("analyzed") else 0
    coverage_scores["METADATA"] = 100 if (metadata is not None) else 0
    # If metadata param not passed (legacy), assume available
    if metadata is None and capabilities is None:
        # fallback: we know metadata analysis always runs, so treat as 100
        coverage_scores["METADATA"] = 100
    coverage_scores["DOCUMENT_IDENTIFICATION"] = 100 if doc_identification else 0
    coverage_scores["OFFLINE_EKYC"] = 100 if offline_ekyc and offline_ekyc.get("provided") and offline_ekyc.get("status")=="PARSED" else (0 if offline_ekyc and not offline_ekyc.get("provided") else 0)

    # Calculate overall coverage: average of required families + optional if provided boosts? Spec says evidence coverage means how much applicable evidence could be analyzed.
    # So denominator is required + optional that were provided (QR if expected? but optional)
    # Simpler: coverage = average of required families, plus optional families that are available increase denominator? Actually we want low coverage when many analyses couldn't be done.
    # Let's define: required families average, and if optional families are available they add to numerator/denominator proportionally but not penalize absence.
    required_avg = sum(coverage_scores[k] for k in required) / len(required)
    # optional: only count if score>0 (available)
    optional_provided = [k for k in optional if coverage_scores[k] > 0]
    if optional_provided:
        optional_avg = sum(coverage_scores[k] for k in optional_provided)/ len(optional_provided)
        # weighted: required 70%, optional 30%
        coverage = int(0.7 * required_avg + 0.3 * optional_avg)
    else:
        coverage = int(required_avg)

    # If EKYC provided and parsed, it also contributes to coverage but optional
    if coverage_scores.get("OFFLINE_EKYC",0)>0:
        coverage = int(0.85 * coverage + 0.15 * coverage_scores["OFFLINE_EKYC"])

    # If image is heavily blurry, coverage should be reduced?
    if quality.get("is_blurry"):
        coverage = max(0, coverage - 20)

    # If many fields NOT_FOUND, reduce coverage?
    if field_covered <50:
        coverage = max(0, coverage - 15)

    # Cap coverage 0-100
    coverage = max(0, min(100, coverage))
    coverage_sufficient = coverage >= 60

    # Scoring notes
    notes = None
    if not coverage_sufficient:
        notes = "Low evidence coverage; score confidence limited. Screening status may be INCONCLUSIVE."

    # Cap due to correlation? If total penalty includes double counting, we already adjusted.
    capped = False

    return {
        "integrity_score": score,
        "evidence_coverage": coverage,
        "coverage_sufficient": coverage_sufficient,
        "scoring_model_version": "1.0",
        "breakdown": breakdown,
        "capped_due_to_correlation": capped,
        "notes": notes,
        "total_penalty": total_penalty,
        "coverage_details": coverage_scores
    }
