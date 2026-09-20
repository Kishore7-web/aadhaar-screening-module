def build_screening(evidence, contradictions, scores, quality, coverage_sufficient=True):
    integrity = scores.get("integrity_score")
    coverage = scores.get("evidence_coverage")
    breakdown = scores.get("breakdown",{})

    # Determine status deterministically
    # Rules:
    # INCONCLUSIVE if coverage <40 or quality very low or insufficient evidence
    # HIGH_REVIEW if multiple strong independent evidences (e.g., >=2 HIGH severity or QR mismatch + forensic + biometric mismatch)
    # REVIEW if any HIGH/MEDIUM meaningful inconsistency
    # LOW_CONCERN if only low findings
    # CLEAR if no major concern and coverage sufficient

    status = "INCONCLUSIVE"
    reasons = []
    evidence_ids = []

    # Check for high severity evidence
    high_ev = [e for e in evidence if e["severity"] in ["HIGH","CRITICAL"] and e["category"] not in ["IMAGE_QUALITY"]]
    medium_ev = [e for e in evidence if e["severity"]=="MEDIUM"]
    low_ev = [e for e in evidence if e["severity"]=="LOW"]

    # Count independent high evidences
    # Group by independent_source and category
    independent_high = [e for e in high_ev if e["independent_source"]]

    # Contradiction count
    contradiction_count = len(contradictions)

    # Coverage check first - INCONCLUSIVE if severely low coverage or very blurry
    if coverage is not None and coverage < 40:
        status = "INCONCLUSIVE"
        reasons.append({"text": f"Insufficient usable evidence (coverage {coverage}%). Image quality or missing data limits analysis.", "evidence_ids": [e["evidence_id"] for e in evidence if e["group"]=="QUALITY"][:2]})
        evidence_ids = [e["evidence_id"] for e in evidence[:3]]
    elif quality.get("is_blurry") and (coverage is None or coverage < 70):
        status = "INCONCLUSIVE"
        reasons.append({"text": "Image is blurry or low quality, limiting reliable extraction.", "evidence_ids": [e["evidence_id"] for e in evidence if e["group"]=="QUALITY"]})
    elif len(independent_high) >= 2:
        # Multiple high-severity independent findings → HIGH_REVIEW (even if same group but multiple distinct findings)
        groups = set(e["group"] for e in independent_high)
        status = "HIGH_REVIEW"
        if len(groups) >= 2:
            reasons.append({"text": f"Multiple independent high-severity findings across {len(groups)} evidence families.", "evidence_ids": [e["evidence_id"] for e in independent_high[:4]]})
        else:
            reasons.append({"text": f"Multiple high-severity findings ({len(independent_high)} distinct).", "evidence_ids": [e["evidence_id"] for e in independent_high[:4]]})
        # Add specific reasons
        for e in independent_high[:3]:
            reasons.append({"text": e["finding"], "evidence_ids": [e["evidence_id"]]})
    elif len(high_ev) >= 2:
        # Two high overall (even if not independent) => HIGH_REVIEW
        status = "HIGH_REVIEW"
        reasons.append({"text": f"Multiple high-severity findings ({len(high_ev)} distinct).", "evidence_ids": [e["evidence_id"] for e in high_ev[:4]]})
        for e in high_ev[:2]:
            reasons.append({"text": e["finding"], "evidence_ids": [e["evidence_id"]]})
    elif len(high_ev) >= 1:
        # single high
        status = "REVIEW"
        for e in high_ev[:2]:
            reasons.append({"text": e["finding"], "evidence_ids": [e["evidence_id"]]})
    elif len(medium_ev) >=2:
        status = "REVIEW"
        for e in medium_ev[:2]:
            reasons.append({"text": e["finding"], "evidence_ids": [e["evidence_id"]]})
    elif len(medium_ev)==1:
        status = "LOW_CONCERN"
        reasons.append({"text": medium_ev[0]["finding"], "evidence_ids": [medium_ev[0]["evidence_id"]]})
    elif len(low_ev)>=1 and not high_ev and not medium_ev:
        status = "LOW_CONCERN"
        reasons.append({"text": low_ev[0]["finding"], "evidence_ids": [low_ev[0]["evidence_id"]]})
    else:
        # No high/medium
        if coverage_sufficient and integrity is not None and integrity >= 80:
            status = "CLEAR"
            reasons.append({"text": "Available evidence is mostly consistent and no significant manipulation signals detected.", "evidence_ids": [e["evidence_id"] for e in evidence if e["severity"]=="INFO"][:3]})
        elif coverage_sufficient and integrity is not None and integrity >= 65:
            status = "LOW_CONCERN"
            reasons.append({"text": "No major inconsistencies detected; minor quality limitations noted.", "evidence_ids": [e["evidence_id"] for e in evidence[:2]]})
        else:
            status = "INCONCLUSIVE"
            reasons.append({"text": "Evidence coverage or quality insufficient for confident assessment.", "evidence_ids": []})

    # Add coverage reason if low but not already inconclusive?
    if status != "INCONCLUSIVE" and coverage is not None and coverage < 60:
        reasons.append({"text": f"Evidence coverage is {coverage}%, some checks could not be performed.", "evidence_ids": []})

    # If status still INCONCLUSIVE but we have no reasons, add generic
    if not reasons:
        reasons.append({"text": "No decisive evidence; manual review recommended.", "evidence_ids": []})

    # Headline
    headlines = {
        "CLEAR": "Document screening completed — no significant concerns detected.",
        "LOW_CONCERN": "Low review priority — minor findings noted.",
        "REVIEW": "Review recommended — meaningful inconsistency or suspicious signal detected.",
        "HIGH_REVIEW": "High review priority due to multiple document inconsistencies.",
        "INCONCLUSIVE": "Inconclusive — insufficient usable evidence for reliable assessment."
    }
    headline = headlines.get(status, "Screening completed.")

    # Recommended action
    actions = {
        "CLEAR": "No immediate action required. Retain evidence trail and proceed per standard workflow. Secondary authorized verification may be performed as per policy.",
        "LOW_CONCERN": "Perform routine verification. If document is critical, consider secondary authorized checks.",
        "REVIEW": "Inspect highlighted fields and suspicious regions. Perform authorized secondary verification via UIDAI-approved service before making a decision.",
        "HIGH_REVIEW": "Do not rely solely on this document. Conduct thorough manual inspection of highlighted regions and perform mandatory authorized secondary verification.",
        "INCONCLUSIVE": "Capture a clearer image and retry. If issue persists, request alternative document or perform authorized in-person verification."
    }
    recommended = actions.get(status, "Manual review recommended.")

    # Next steps
    next_steps = []
    if status in ["REVIEW","HIGH_REVIEW"]:
        next_steps.append("Inspect the highlighted DOB/Name/Number fields and QR comparison table.")
        if any(e["group"]=="FORENSICS" for e in evidence if e["severity"] in ["MEDIUM","HIGH"]):
            next_steps.append("Review forensic annotated image and suspicious region crops.")
        if any(e["group"]=="BIOMETRIC" for e in evidence if e["severity"]=="HIGH"):
            next_steps.append("Re-validate identity with a fresh reference photograph or biometric check.")
        next_steps.append("Perform authorized secondary verification via UIDAI eKYC / QR verifier where permitted.")
    elif status == "INCONCLUSIVE":
        next_steps.append("Re-capture document with better lighting, focus, and full frame.")
        next_steps.append("Ensure QR code is clearly visible and not cropped.")
        next_steps.append("If document is physical, try scanning at 300 DPI.")
    else:
        next_steps.append("Archive audit hash and evidence manifest for traceability.")
        next_steps.append("Proceed per organizational policy; no automated rejection based on this screening alone.")

    # Limitations
    limitations = [
        "Official UIDAI authentication was not performed.",
        "This is an AI-assisted screening system, not an official verification service.",
        "Results are based on available evidence quality; low coverage reduces certainty."
    ]
    if coverage is not None and coverage < 60:
        limitations.append(f"Evidence coverage was {coverage}%; several checks were limited by image quality or missing data.")
    if not any(e["source"]=="QR" and e["category"]=="QR" for e in evidence if "decoded" in e["finding"]):
        limitations.append("QR cryptographic signature verification was not configured in this environment (NOT_CONFIGURED).")

    # Collect evidence_ids for screening
    all_eids = []
    for r in reasons:
        all_eids.extend(r["evidence_ids"])
    all_eids = list(set(all_eids))[:10]

    return {
        "status": status,
        "headline": headline,
        "reasons": reasons,
        "recommended_action": recommended,
        "next_steps": next_steps,
        "limitations": limitations,
        "evidence_ids": all_eids
    }
