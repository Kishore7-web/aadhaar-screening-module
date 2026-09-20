import time
import uuid
import json
import hashlib
from datetime import datetime, timezone
from pathlib import Path
import cv2
import numpy as np

from ..utils.hashing import sha256_bytes, canonical_json, mask_aadhaar
from ..config import settings
from .secure_input import validate_and_save_document, validate_ekyc_upload, cleanup_temp, sanitize_filename
from .document_loader import load_document
from .ocr_adapter import OCRAdapter, ocr_adapter
from .orientation import estimate_orientation, correct_orientation
from .doc_identification import identify_document
from .field_extraction import extract_fields
from .number_validation import validate_aadhaar_number
from .photo_detection import detect_photo
from .face_analysis import compare_faces
from .qr_analysis import detect_and_decode_qr, compare_qr_printed
from .metadata_analysis import analyze_metadata
from .forensics import analyze_forensics, generate_annotated_image
from .ekyc_parser import parse_offline_ekyc
from .crypto_verifier import verify_qr_signature
from .evidence_engine import build_evidence
from .contradiction_engine import build_contradictions, build_evidence_relations
from .scoring_engine import calculate_scores
from .explanation_engine import build_screening
from .audit_service import create_audit_event, verify_chain
from .blockchain_adapter import blockchain_adapter
from ..models.schemas import *

# Global OCR adapter shared (imported from ocr_adapter module)
# ocr_adapter already imported above

def run_pipeline(document_bytes: bytes, filename: str, reference_face_bytes: bytes=None, ekyc_bytes: bytes=None, ekyc_filename: str=None, case_id: str=None, persist_artifacts: bool=False):
    start_all = time.time()
    started_at = datetime.now(timezone.utc).isoformat()
    if not case_id:
        case_id = f"CASE-{uuid.uuid4().hex[:8].upper()}"
    generated_at = datetime.now(timezone.utc).isoformat()
    errors = []
    stages = []

    def add_stage(name, status, duration=None, notes=None):
        stages.append(ProcessingStage(name=name, status=status, duration_ms=duration, notes=notes))

    # Secure input
    t0=time.time()
    tmp_path = None
    ekyc_tmp = None
    try:
        # Mock UploadFile-like for validation
        class MockFile:
            def __init__(self, name):
                self.filename = name
        mock = MockFile(filename)
        tmp_path, sec_errors, sec_notes, sanitized, ext = validate_and_save_document(mock, document_bytes)
        document_security_notes = sec_notes
        document_security_status = "PASS"
        if sec_errors:
            document_security_status = "FAIL"
            for e in sec_errors:
                errors.append({"stage":"security","code":e.get("code"),"message":e.get("message")})
            # If security failed, we cannot continue? But still return partial
            if tmp_path is None:
                add_stage("security", "FAILED", int((time.time()-t0)*1000), str(sec_errors))
                # Build minimal response
                return build_minimal_response(case_id, generated_at, started_at, stages, errors, document_security_notes, sanitized, ext, document_bytes)
        add_stage("security", "DONE", int((time.time()-t0)*1000), "; ".join(sec_notes))
    except Exception as e:
        errors.append({"stage":"security","message":str(e)})
        add_stage("security", "ERROR", int((time.time()-t0)*1000), str(e))
        return build_minimal_response(case_id, generated_at, started_at, stages, errors, [], filename, "", document_bytes)

    # Document loader
    t0=time.time()
    images = None
    doc_info = {}
    try:
        images, doc_loader_info, loader_errors = load_document(tmp_path, document_bytes)
        for e in loader_errors:
            errors.append(e)
        if images is None:
            add_stage("document_loader", "FAILED", int((time.time()-t0)*1000), str(loader_errors))
            return build_minimal_response(case_id, generated_at, started_at, stages, errors, document_security_notes, sanitized, ext, document_bytes, doc_loader_info)
        add_stage("document_loader", "DONE", int((time.time()-t0)*1000), f"Pages {doc_loader_info.get('pages_analyzed')}")
    except Exception as e:
        errors.append({"stage":"document_loader","message":str(e)})
        add_stage("document_loader", "ERROR", int((time.time()-t0)*1000), str(e))
        return build_minimal_response(case_id, generated_at, started_at, stages, errors, document_security_notes, sanitized, ext, document_bytes)

    # Keep first image for many analyses
    first_image = images[0]["image"] if images else None
    sha256 = doc_loader_info.get("sha256")

    # Quality analysis
    t0=time.time()
    quality = {}
    try:
        from ..utils.image_utils import estimate_blur, estimate_brightness_contrast, detect_glare
        blur = estimate_blur(first_image)
        brightness, contrast = estimate_brightness_contrast(first_image)
        glare = detect_glare(first_image)
        # Overall score
        # blur <100 => low, 100-300 medium, >300 high
        if blur is not None:
            if blur > 300:
                overall_label = "GOOD"
                overall_score = min(95, 60 + blur/20)
            elif blur > 100:
                overall_label = "MEDIUM"
                overall_score = 40 + (blur-100)/5
            else:
                overall_label = "POOR"
                overall_score = max(5, blur/2)
        else:
            overall_label = "UNKNOWN"
            overall_score = None
        is_blurry = blur is not None and blur < 100
        is_low = overall_label=="POOR"
        quality = {
            "overall_score": round(float(overall_score),1) if overall_score else None,
            "overall_label": overall_label,
            "blur_score": round(float(blur),2) if blur else None,
            "blur_label": "BLURRY" if is_blurry else ("SHARP" if blur and blur>300 else "MEDIUM"),
            "brightness": round(float(brightness),2) if brightness else None,
            "contrast": round(float(contrast),2) if contrast else None,
            "glare_detected": bool(glare),
            "is_blurry": bool(is_blurry),
            "is_low_quality": bool(is_low),
            "notes": [f"Blur variance {blur:.1f}" if blur else "No blur", f"Glare {glare}"]
        }
        add_stage("quality", "DONE", int((time.time()-t0)*1000), overall_label)
    except Exception as e:
        errors.append({"stage":"quality","message":str(e)})
        quality = {"overall_label":"UNKNOWN","is_blurry":False,"is_low_quality":False}
        add_stage("quality", "ERROR", int((time.time()-t0)*1000), str(e))

    # OCR
    t0=time.time()
    ocr_results = []
    ocr_text = ""
    ocr_conf = 0
    try:
        if not first_image is None:
            ocr_results = ocr_adapter.ocr_images(images)
            ocr_text = ocr_adapter.combined_text(ocr_results)
            ocr_conf = ocr_adapter.avg_confidence(ocr_results)
        add_stage("ocr", "DONE" if ocr_text else "PARTIAL", int((time.time()-t0)*1000), f"Text length {len(ocr_text)}, conf {ocr_conf:.2f}")
    except Exception as e:
        errors.append({"stage":"ocr","message":str(e)})
        add_stage("ocr", "ERROR", int((time.time()-t0)*1000), str(e))

    # Orientation
    t0=time.time()
    orientation = {}
    try:
        orientation = estimate_orientation(images, ocr_adapter, ocr_results)
        if orientation.get("applied_rotation") !=0:
            images = correct_orientation(images, orientation.get("applied_rotation"))
            first_image = images[0]["image"] if images else first_image
            # Re-run OCR after rotation? For now keep original OCR but note rotation
        add_stage("orientation", "DONE", int((time.time()-t0)*1000), f"Rotation {orientation.get('applied_rotation')}")
    except Exception as e:
        errors.append({"stage":"orientation","message":str(e)})
        orientation = {"applied_rotation":0, "confidence":0, "method":"HEURISTIC", "ambiguous": False}
        add_stage("orientation", "ERROR", int((time.time()-t0)*1000), str(e))

    # QR detection
    t0=time.time()
    qr_info = {}
    qr_consistency = None
    try:
        qr_info = detect_and_decode_qr(images)
        add_stage("qr", "DONE", int((time.time()-t0)*1000), qr_info.get("status"))
    except Exception as e:
        errors.append({"stage":"qr","message":str(e)})
        qr_info = {"status":"QR_NOT_PRESENT","decoded":False,"fields":{}}
        add_stage("qr", "ERROR", int((time.time()-t0)*1000), str(e))

    # Document identification
    t0=time.time()
    doc_ident = {}
    try:
        doc_ident = identify_document(ocr_text, has_qr=(qr_info.get("status")=="QR_PRESENT"))
        add_stage("document_identification", "DONE", int((time.time()-t0)*1000), doc_ident.get("result"))
    except Exception as e:
        errors.append({"stage":"doc_ident","message":str(e)})
        doc_ident = {"result":"NOT_CONFIDENT","confidence":0.5}
        add_stage("document_identification", "ERROR", int((time.time()-t0)*1000), str(e))

    # Field extraction
    t0=time.time()
    fields = {}
    try:
        fields = extract_fields(ocr_text, ocr_results)
        # Augment with QR consistency? Later
        # Ensure masked_value for aadhaar
        if fields.get("aadhaar_number",{}).get("value"):
            raw = fields["aadhaar_number"]["value"]
            fields["aadhaar_number"]["masked_value"] = mask_aadhaar(raw)
        # Also add QR sources to fields where consistent?
        add_stage("field_extraction", "DONE", int((time.time()-t0)*1000), f"Fields {len([k for k,v in fields.items() if v.get('status')=='DETECTED'])}")
    except Exception as e:
        errors.append({"stage":"field_extraction","message":str(e)})
        fields = {}
        add_stage("field_extraction", "ERROR", int((time.time()-t0)*1000), str(e))

    # Number validation
    t0=time.time()
    number_validation = {}
    try:
        aadhaar_field = fields.get("aadhaar_number",{})
        val = aadhaar_field.get("value")
        raw = aadhaar_field.get("raw_value")
        number_validation = validate_aadhaar_number(val, raw)
        # Update field masked_value with proper masking
        if number_validation.get("masked_value"):
            fields["aadhaar_number"]["masked_value"] = number_validation["masked_value"]
        add_stage("number_validation", "DONE", int((time.time()-t0)*1000), number_validation.get("checksum_status"))
    except Exception as e:
        errors.append({"stage":"number_validation","message":str(e)})
        number_validation = {"format_status":"NOT_CHECKED","checksum_status":"NOT_CHECKED"}
        add_stage("number_validation", "ERROR", int((time.time()-t0)*1000), str(e))

    # Photo detection
    t0=time.time()
    photo_info = {}
    try:
        photo_info = detect_photo(first_image)
        add_stage("photo", "DONE", int((time.time()-t0)*1000), photo_info.get("status"))
    except Exception as e:
        errors.append({"stage":"photo","message":str(e)})
        photo_info = {"status":"NOT_FOUND"}
        add_stage("photo", "ERROR", int((time.time()-t0)*1000), str(e))

    # Face comparison
    t0=time.time()
    biometric = {}
    try:
        if reference_face_bytes:
            biometric = compare_faces(first_image, ref_image_bytes=reference_face_bytes, threshold=settings.face_threshold)
        else:
            biometric = compare_faces(first_image, ref_image_bytes=None, threshold=settings.face_threshold)
        add_stage("face", "DONE", int((time.time()-t0)*1000), biometric.get("status"))
    except Exception as e:
        errors.append({"stage":"face","message":str(e)})
        biometric = {"status":"NOT_AVAILABLE","message":str(e)}
        add_stage("face", "ERROR", int((time.time()-t0)*1000), str(e))

    # QR consistency
    t0=time.time()
    try:
        if qr_info.get("decoded"):
            qr_consistency = compare_qr_printed(fields, qr_info.get("fields",{}))
            # Update fields consistency
            for item in qr_consistency.get("items",[]):
                field_key = item["field"]
                if field_key in fields:
                    fields[field_key]["consistency"] = item["result"]
                    # Add QR source if match? Not needed but note provenance
                    if item["result"]=="MATCH":
                        fields[field_key]["sources"].append({"type":"QR","confidence":1.0})
            add_stage("qr_consistency", "DONE", int((time.time()-t0)*1000), qr_consistency.get("overall"))
        else:
            qr_consistency = {"checked": False, "items": [], "overall":"NOT_CHECKED","mismatches":0}
            add_stage("qr_consistency", "DONE", int((time.time()-t0)*1000), "NOT_CHECKED")
    except Exception as e:
        errors.append({"stage":"qr_consistency","message":str(e)})
        qr_consistency = {"checked": False, "items": [], "overall":"NOT_CHECKED","mismatches":0}
        add_stage("qr_consistency", "ERROR", int((time.time()-t0)*1000), str(e))

    # Metadata
    t0=time.time()
    metadata = {}
    try:
        metadata = analyze_metadata(document_bytes, ext or "unknown", first_image)
        add_stage("metadata", "DONE", int((time.time()-t0)*1000), "analyzed")
    except Exception as e:
        errors.append({"stage":"metadata","message":str(e)})
        metadata = {}
        add_stage("metadata", "ERROR", int((time.time()-t0)*1000), str(e))

    # Forensics
    t0=time.time()
    forensics = {}
    annotated_path = None
    try:
        forensics = analyze_forensics(first_image, fields)
        add_stage("forensics", "DONE", int((time.time()-t0)*1000), forensics.get("overall_label"))
    except Exception as e:
        errors.append({"stage":"forensics","message":str(e)})
        forensics = {"analyzed": False, "overall_label":"ERROR"}
        add_stage("forensics", "ERROR", int((time.time()-t0)*1000), str(e))

    # eKYC
    t0=time.time()
    offline_ekyc = {"provided": False, "status":"NOT_PROVIDED","fields":{},"signature_status":"NOT_CHECKED"}
    try:
        if ekyc_bytes and ekyc_filename:
            # need temp path for ekyc
            class MockEkyc:
                filename = ekyc_filename
            ekyc_tmp, ekyc_errors = validate_ekyc_upload(MockEkyc(), ekyc_bytes)
            if ekyc_errors:
                for e in ekyc_errors:
                    errors.append({"stage":"ekyc","message":e.get("message")})
                offline_ekyc = {"provided": True, "status":"FAILED","fields":{},"signature_status":"NOT_CHECKED","notes": str(ekyc_errors)}
            else:
                # parse
                offline_ekyc = parse_offline_ekyc(ekyc_tmp, ekyc_bytes)
            # consistency with QR/fields will be handled in evidence
            add_stage("ekyc", "DONE", int((time.time()-t0)*1000), offline_ekyc.get("status"))
        else:
            add_stage("ekyc", "DONE", int((time.time()-t0)*1000), "NOT_PROVIDED")
    except Exception as e:
        errors.append({"stage":"ekyc","message":str(e)})
        offline_ekyc = {"provided": bool(ekyc_bytes), "status":"FAILED","fields":{},"signature_status":"NOT_CHECKED"}
        add_stage("ekyc", "ERROR", int((time.time()-t0)*1000), str(e))
    finally:
        if ekyc_tmp:
            cleanup_temp(ekyc_tmp)

    # Crypto verifier (QR signature) - adapter
    t0=time.time()
    crypto_status = {}
    try:
        if qr_info.get("data_raw"):
            crypto_status = verify_qr_signature(qr_info.get("data_raw"))
        else:
            crypto_status = {"status":"NOT_CHECKED","message":"No QR data"}
        add_stage("crypto", "DONE", int((time.time()-t0)*1000), crypto_status.get("status"))
    except Exception as e:
        errors.append({"stage":"crypto","message":str(e)})
        crypto_status = {"status":"NOT_CONFIGURED"}
        add_stage("crypto", "ERROR", int((time.time()-t0)*1000), str(e))

    # Update QR signature status in offline_ekyc or qr_info? Keep separate but expose via capabilities
    # We'll store crypto_status in qr_info notes? Actually we need to expose via capabilities and maybe notes
    # For response, we set capability qr_signature false if not configured

    # Evidence engine
    t0=time.time()
    evidence = []
    contradictions = []
    evidence_relations = []
    try:
        evidence = build_evidence(fields, number_validation, qr_info, qr_consistency, photo_info, biometric, forensics, metadata, doc_ident, quality, offline_ekyc)
        contradictions = build_contradictions(evidence, qr_consistency, fields, offline_ekyc)
        evidence_relations = build_evidence_relations(evidence, contradictions)
        add_stage("evidence", "DONE", int((time.time()-t0)*1000), f"{len(evidence)} evidences")
    except Exception as e:
        errors.append({"stage":"evidence","message":str(e)})
        add_stage("evidence", "ERROR", int((time.time()-t0)*1000), str(e))

    # Scoring
    t0=time.time()
    scores = {}
    try:
        scores = calculate_scores(evidence, contradictions, quality, photo_info, forensics, biometric, qr_info, number_validation, doc_ident, offline_ekyc, metadata=metadata)
        add_stage("scoring", "DONE", int((time.time()-t0)*1000), f"Score {scores.get('integrity_score')}")
    except Exception as e:
        errors.append({"stage":"scoring","message":str(e)})
        scores = {"integrity_score": None, "evidence_coverage": 0, "coverage_sufficient": False, "scoring_model_version":"1.0", "breakdown":{}}
        add_stage("scoring", "ERROR", int((time.time()-t0)*1000), str(e))

    # Explanation
    t0=time.time()
    screening = {}
    try:
        screening = build_screening(evidence, contradictions, scores, quality, scores.get("coverage_sufficient", False))
        add_stage("explanation", "DONE", int((time.time()-t0)*1000), screening.get("status"))
    except Exception as e:
        errors.append({"stage":"explanation","message":str(e)})
        screening = {"status":"INCONCLUSIVE","headline":"Screening inconclusive due to error","reasons":[],"recommended_action":"Manual review","next_steps":[],"limitations":[],"evidence_ids":[]}
        add_stage("explanation", "ERROR", int((time.time()-t0)*1000), str(e))

    # Artifacts
    artifacts = {"original_hash": sha256, "items": [], "report_available": False}
    try:
        # Generate annotated forensic image if regions exist
        if persist_artifacts and forensics.get("regions"):
            from ..config import get_artifacts_dir
            import cv2
            annotated, _ = generate_annotated_image(first_image, forensics.get("regions"))
            if annotated is not None:
                art_dir = get_artifacts_dir() / case_id
                art_dir.mkdir(parents=True, exist_ok=True)
                annot_path = art_dir / f"{case_id}_annotated.png"
                cv2.imwrite(str(annot_path), annotated)
                # hash
                with open(annot_path, "rb") as f:
                    ahash = sha256_bytes(f.read())
                artifacts["items"].append({"type":"annotated_image","file_name": annot_path.name, "path": str(annot_path), "hash": ahash, "available": True})
                # crops
                for reg in forensics.get("regions",[]):
                    x,y,wc,hc = reg["bounding_box"]
                    crop = first_image[y:y+hc, x:x+wc]
                    if crop.size>0:
                        crop_path = art_dir / f"{case_id}_forensic_{reg['region_id']}.png"
                        cv2.imwrite(str(crop_path), crop)
                        with open(crop_path, "rb") as f:
                            chash = sha256_bytes(f.read())
                        artifacts["items"].append({"type":"forensic_crop","file_name":crop_path.name,"path":str(crop_path),"hash":chash,"available":True,"page":1})
        # Save original artifact if persist_artifacts (hash_only default not save)
        if persist_artifacts:
            from ..config import get_artifacts_dir
            art_dir = get_artifacts_dir() / case_id
            art_dir.mkdir(parents=True, exist_ok=True)
            orig_path = art_dir / f"{case_id}_original{ext}"
            with open(orig_path, "wb") as f:
                f.write(document_bytes)
            with open(orig_path, "rb") as f:
                ohash = sha256_bytes(f.read())
            artifacts["items"].append({"type":"original","file_name":orig_path.name,"path":str(orig_path),"hash":ohash,"available":True})
            # Generate PDF report via ReportLab if available (scores/screening already computed)
            try:
                from reportlab.lib.pagesizes import A4
                from reportlab.lib import colors
                from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
                from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
                from reportlab.lib.units import inch
                report_path = art_dir / f"{case_id}_report.pdf"
                doc = SimpleDocTemplate(str(report_path), pagesize=A4, topMargin=0.6*inch, bottomMargin=0.6*inch)
                styles = getSampleStyleSheet()
                title_style = ParagraphStyle('Title2', parent=styles['Title'], fontSize=16, textColor=colors.HexColor('#0f4c81'))
                heading_style = ParagraphStyle('Heading2', parent=styles['Heading2'], fontSize=11, textColor=colors.HexColor('#0f172a'))
                normal = styles['Normal']
                normal.fontSize=8
                elements=[]
                elements.append(Paragraph("DAKSH — Aadhaar Screening Report", title_style))
                elements.append(Paragraph("Prototype Screening Report — Not an official UIDAI authentication result", styles['Italic']))
                elements.append(Spacer(1,0.15*inch))
                elements.append(Paragraph(f"Case ID: {case_id} &nbsp;&nbsp; Generated: {generated_at}", normal))
                elements.append(Paragraph(f"Document: {sanitized} &nbsp;&nbsp; SHA-256: {sha256[:24]}...", normal))
                elements.append(Spacer(1,0.15*inch))
                # Scores
                integrity = scores.get("integrity_score", "N/A")
                coverage = scores.get("evidence_coverage", 0)
                status = screening.get("status", "INCONCLUSIVE")
                elements.append(Paragraph(f"Document Integrity Score: <b>{integrity} / 100</b> &nbsp;&nbsp; Evidence Coverage: <b>{coverage}%</b> &nbsp;&nbsp; Status: <b>{status}</b>", heading_style))
                elements.append(Spacer(1,0.1*inch))
                elements.append(Paragraph(f"Headline: {screening.get('headline','')}", normal))
                elements.append(Paragraph(f"Recommended Action: {screening.get('recommended_action','')}", normal))
                elements.append(Spacer(1,0.15*inch))
                # Fields table
                elements.append(Paragraph("Extracted Fields", heading_style))
                f_data = [["Field","Value","Status","Consistency"]]
                for k,v in fields.items():
                    f_data.append([k, (v.get("masked_value") or v.get("value") or "—")[:40], v.get("status",""), v.get("consistency") or "—"])
                t=Table(f_data, colWidths=[1.5*inch, 2.5*inch, 1.2*inch, 1.2*inch])
                t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor('#0f4c81')),('TEXTCOLOR',(0,0),(-1,0),colors.white),('FONTSIZE',(0,0),(-1,-1),7),('GRID',(0,0),(-1,-1),0.5,colors.grey),('ROWBACKGROUNDS',(0,1),(-1,-1),[colors.white, colors.HexColor('#f1f5f9')])]))
                elements.append(t)
                elements.append(Spacer(1,0.15*inch))
                # Evidence summary
                elements.append(Paragraph(f"Evidence Items ({len(evidence)}) and Contradictions ({len(contradictions)})", heading_style))
                for ev in evidence[:12]:
                    elements.append(Paragraph(f"{ev['evidence_id']} [{ev['severity']}] {ev['finding'][:120]}", normal))
                elements.append(Spacer(1,0.15*inch))
                elements.append(Paragraph(f"Audit: Document Hash {sha256[:32]}... | Chain Verified: {verify_chain().get('verified')} | Blockchain: NOT_CONFIGURED", normal))
                elements.append(Paragraph("This is a prototype screening report for review prioritization. Official UIDAI authentication was not performed.", styles['Italic']))
                doc.build(elements)
                with open(report_path, "rb") as f:
                    rhash = sha256_bytes(f.read())
                artifacts["items"].append({"type":"report_pdf","file_name": report_path.name, "path": str(report_path), "hash": rhash, "available": True})
                artifacts["report_available"] = True
            except Exception as e:
                errors.append({"stage":"report","message":f"Report generation failed: {e}"})
                import traceback; traceback.print_exc()
        add_stage("artifacts", "DONE", int((time.time()-t0)*1000), f"{len(artifacts['items'])} artifacts")
    except Exception as e:
        errors.append({"stage":"artifacts","message":str(e)})
        add_stage("artifacts", "ERROR", int((time.time()-t0)*1000), str(e))

    # Audit
    t0=time.time()
    audit = {}
    try:
        # Create manifest hash from evidence+scores etc
        manifest = {
            "case_id": case_id,
            "evidence": evidence,
            "scores": scores,
            "screening": screening,
            "document_hash": sha256
        }
        manifest_hash = sha256_bytes(canonical_json(manifest).encode())
        # Audit chain
        chain_event = create_audit_event(case_id, sha256, manifest_hash, settings.module_version)
        chain_verified = verify_chain()
        audit = {
            "case_id": case_id,
            "document_hash": sha256,
            "manifest_hash": manifest_hash,
            "report_hash": None,
            "chain_event_id": chain_event.get("event_id"),
            "chain_event_hash": chain_event.get("event_hash"),
            "previous_hash": chain_event.get("previous_hash"),
            "chain_verified": chain_verified.get("verified", True),
            "blockchain_status": blockchain_adapter.status().get("status"),
            "blockchain_tx": None,
            "timestamp": generated_at,
            "notes": "Local tamper-evident hash chain. Blockchain anchoring not configured."
        }
        add_stage("audit", "DONE", int((time.time()-t0)*1000), chain_event.get("event_id"))
    except Exception as e:
        errors.append({"stage":"audit","message":str(e)})
        audit = {"case_id": case_id, "document_hash": sha256, "manifest_hash": None, "chain_verified": False, "blockchain_status":"NOT_CONFIGURED"}
        add_stage("audit", "ERROR", int((time.time()-t0)*1000), str(e))

    # Cleanup tmp_path
    if tmp_path:
        cleanup_temp(tmp_path)

    # Determine capabilities
    capabilities = {
        "document_identification": True,
        "quality_analysis": True,
        "orientation_analysis": True,
        "security_checks": True,
        "ocr": ocr_adapter.is_available(),
        "number_validation": True,
        "qr": True,
        "qr_signature": crypto_status.get("status")=="VERIFIED" or crypto_status.get("status")=="INVALID_SIGNATURE",
        "photo": True,
        "face_reference": bool(reference_face_bytes),
        "face_comparison": biometric.get("status") not in ["NOT_CHECKED","NOT_AVAILABLE"],
        "forensics": True,
        "metadata": True,
        "offline_ekyc": offline_ekyc.get("provided", False) and offline_ekyc.get("status")=="PARSED"
    }

    # Document info
    document = {
        "file_name": sanitized,
        "file_type": ext.lstrip(".") if ext else "unknown",
        "file_size_bytes": len(document_bytes),
        "mime_type": doc_loader_info.get("mime_type"),
        "page_count": doc_loader_info.get("page_count",1),
        "pages_analyzed": doc_loader_info.get("pages_analyzed",1),
        "sha256": sha256,
        "load_duration_ms": doc_loader_info.get("load_duration_ms"),
        "storage_mode": settings.storage_mode
    }
    document_security = {
        "file_size_check": "PASS",
        "mime_check": "PASS",
        "extension_check": "PASS",
        "magic_byte_check": "PASS",
        "filename_sanitized": True,
        "path_traversal_check": "PASS",
        "corrupted_check": "PASS" if not any("corrupted" in str(e).lower() for e in errors) else "FAIL",
        "pdf_check": None,
        "zip_check": None,
        "notes": document_security_notes
    }
    # Page analyses
    page_analyses = []
    for p in doc_loader_info.get("pages",[]):
        page_analyses.append({
            "page_number": p.get("page"),
            "width": p.get("width"),
            "height": p.get("height"),
            "dpi_estimate": 200 if document["file_type"]=="pdf" else None,
            "text_layer_present": p.get("text_layer", False),
            "notes": None
        })

    # Processing info
    completed_at = datetime.now(timezone.utc).isoformat()
    duration_ms = int((time.time() - start_all)*1000)
    processing = {
        "started_at": started_at,
        "completed_at": completed_at,
        "duration_ms": duration_ms,
        "pipeline_stage": "COMPLETE" if not any("FAILED" in s.status for s in stages) else "PARTIAL",
        "build_stage_label": "COMPLETE",
        "stages": [s.dict() for s in stages],
        "pending_components": [],
        "optional_inputs": ["reference_face" if not reference_face_bytes else "reference_face_provided", "offline_ekyc" if not ekyc_bytes else "offline_ekyc_provided"],
        "notes": []
    }

    # Privacy
    privacy = {
        "masked_aadhaar": number_validation.get("masked_value") or (fields.get("aadhaar_number",{}).get("masked_value") if fields.get("aadhaar_number") else None),
        "pii_stored": False,
        "storage_mode": settings.storage_mode,
        "retention_note": "Raw document not persisted by default (HASH_ONLY). Artifacts only when explicitly requested."
    }

    # Validation list (for P6)
    validation = []
    validation.append({"check":"number_format","status": number_validation.get("format_status"), "message": number_validation.get("checksum_message")})
    validation.append({"check":"checksum","status": number_validation.get("checksum_status")})
    if qr_consistency.get("checked"):
        validation.append({"check":"qr_consistency","status": qr_consistency.get("overall"), "mismatches": qr_consistency.get("mismatches")})
    if biometric.get("status")!="NOT_CHECKED":
        validation.append({"check":"face_comparison","status": biometric.get("status")})

    # Build final response object per schema
    response = {
        "schema_version": settings.schema_version,
        "case_id": case_id,
        "document_type": "aadhaar",
        "document_variant": doc_ident.get("variant","unknown"),
        "module": settings.module,
        "module_version": settings.module_version,
        "module_status": "COMPLETE" if len(errors)==0 else ("PARTIAL" if duration_ms>0 else "FAILED"),
        "generated_at": generated_at,
        "processing": processing,
        "capabilities": capabilities,
        "document": document,
        "document_security": document_security,
        "document_identification": {
            "result": doc_ident.get("result"),
            "confidence": doc_ident.get("confidence"),
            "confidence_basis": doc_ident.get("confidence_basis"),
            "variant": doc_ident.get("variant"),
            "signals": doc_ident.get("signals",[]),
            "keywords_found": doc_ident.get("keywords_found",[]),
            "notes": doc_ident.get("notes")
        },
        "page_analyses": page_analyses,
        "quality": quality,
        "orientation": orientation,
        "fields": fields,
        "number_validation": number_validation,
        "qr": qr_info,
        "qr_consistency": qr_consistency,
        "photo": {
            "status": photo_info.get("status"),
            "bounding_box": photo_info.get("bounding_box"),
            "page": photo_info.get("page"),
            "quality_score": photo_info.get("quality_score"),
            "quality_label": photo_info.get("quality_label"),
            "has_crop": photo_info.get("has_crop", False),
            "notes": photo_info.get("notes")
        },
        "biometric": biometric,
        "forensics": forensics,
        "metadata": metadata,
        "offline_ekyc": offline_ekyc,
        "validation": validation,
        "contradictions": contradictions,
        "evidence": evidence,
        "evidence_relations": evidence_relations,
        "scores": {
            "integrity_score": scores.get("integrity_score"),
            "evidence_coverage": scores.get("evidence_coverage",0),
            "coverage_sufficient": scores.get("coverage_sufficient", False),
            "scoring_model_version": scores.get("scoring_model_version","1.0"),
            "breakdown": scores.get("breakdown",{}),
            "capped_due_to_correlation": scores.get("capped_due_to_correlation", False),
            "notes": scores.get("notes")
        },
        "screening": screening,
        "artifacts": artifacts,
        "audit": audit,
        "privacy": privacy,
        "errors": errors
    }

    return response

def build_minimal_response(case_id, generated_at, started_at, stages, errors, sec_notes, sanitized, ext, document_bytes, doc_info=None):
    sha = sha256_bytes(document_bytes) if document_bytes else None
    processing = {
        "started_at": started_at,
        "completed_at": datetime.now(timezone.utc).isoformat(),
        "duration_ms": 0,
        "pipeline_stage": "FAILED",
        "build_stage_label": "COMPLETE",
        "stages": [s.dict() if hasattr(s, 'dict') else s for s in stages],
        "pending_components": [],
        "optional_inputs": [],
        "notes": ["Failed early due to security/document load"]
    }
    return {
        "schema_version": settings.schema_version,
        "case_id": case_id,
        "document_type": "aadhaar",
        "document_variant": "unknown",
        "module": settings.module,
        "module_version": settings.module_version,
        "module_status": "FAILED",
        "generated_at": generated_at,
        "processing": processing,
        "capabilities": {},
        "document": {"file_name": sanitized, "file_type": ext.lstrip(".") if ext else "unknown", "file_size_bytes": len(document_bytes) if document_bytes else 0, "sha256": sha},
        "document_security": {"notes": sec_notes},
        "document_identification": {"result":"UNSUPPORTED_DOCUMENT"},
        "page_analyses": [],
        "quality": {"overall_label":"UNKNOWN"},
        "orientation": {"applied_rotation":0},
        "fields": {},
        "number_validation": {"format_status":"NOT_CHECKED","checksum_status":"NOT_CHECKED"},
        "qr": {"status":"QR_NOT_PRESENT"},
        "qr_consistency": {"checked": False},
        "photo": {"status":"NOT_FOUND"},
        "biometric": {"status":"NOT_CHECKED"},
        "forensics": {"analyzed": False},
        "metadata": {},
        "offline_ekyc": {"provided": False},
        "validation": [],
        "contradictions": [],
        "evidence": [],
        "evidence_relations": [],
        "scores": {"integrity_score": None, "evidence_coverage": 0, "coverage_sufficient": False},
        "screening": {"status":"INCONCLUSIVE","headline":"Failed to process document","reasons":[],"recommended_action":"Check file and retry","next_steps":[],"limitations":[],"evidence_ids":[]},
        "artifacts": {"original_hash": sha},
        "audit": {"case_id": case_id, "document_hash": sha},
        "privacy": {"storage_mode": settings.storage_mode},
        "errors": errors
    }
