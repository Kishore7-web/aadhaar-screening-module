from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from typing import Optional
import time
import platform
import sys
from pathlib import Path

from .config import settings, PROJECT_ROOT, get_artifacts_dir, get_audit_chain_path
from .services.pipeline import run_pipeline
from .services.storage import repo
from .services.audit_service import verify_chain, get_chain_tail
from .services.ocr_adapter import ocr_adapter

app = FastAPI(
    title="DAKSH Aadhaar Screening - P3 Module",
    description="AI-Assisted Aadhaar Document Screening & Evidence Fusion - Ministry of Home Affairs SSB - SIH 2026",
    version=settings.module_version,
)

# CORS
origins = [o.strip() for o in settings.allow_origins.split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins if origins else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

start_time = time.time()
requests_served = 0

@app.get("/api/health")
def health():
    return {
        "status": "ok",
        "service": "daksh-aadhaar-p3",
        "module": settings.module,
        "module_version": settings.module_version,
        "schema_version": settings.schema_version,
        "build_stage": settings.build_stage,
        "environment": settings.environment,
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "components": {
            "ocr": "available" if ocr_adapter.is_available() else "not_available",
            "forensics": "available",
            "face": "available",
            "qr": "available",
            "audit_chain": "available",
            "storage": "available"
        },
        "warnings": []
    }

@app.get("/api/health/details")
def health_details():
    global requests_served
    audit_path = get_audit_chain_path()
    art_dir = get_artifacts_dir()
    return {
        "status": "ok",
        "service": "daksh-aadhaar-p3",
        "module": settings.module,
        "module_version": settings.module_version,
        "schema_version": settings.schema_version,
        "build_stage": settings.build_stage,
        "environment": settings.environment,
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "python_version": sys.version,
        "platform": platform.platform(),
        "uptime_seconds": int(time.time() - start_time),
        "requests_served": requests_served,
        "config": {
            "storage_mode": settings.storage_mode,
            "artifacts_dir": str(art_dir),
            "max_file_size_mb": settings.max_file_size_mb,
            "ocr_engine": settings.ocr_engine,
            "face_threshold": settings.face_threshold
        },
        "directories": {
            "artifacts_exists": art_dir.exists(),
            "audit_chain_exists": audit_path.exists()
        },
        "storage": {
            "local_cases": len(list((art_dir / "cases").glob("*.json"))) if (art_dir / "cases").exists() else 0
        },
        "models": {
            "ocr_available": ocr_adapter.is_available(),
            "ocr_engine": ocr_adapter.current_engine_name,
            "face_model": "OpenCV-Haar+Histogram"
        },
        "ocr_status": "available" if ocr_adapter.is_available() else "fallback",
        "database_status": "local_fallback",
        "audit_status": verify_chain()
    }

@app.post("/api/modules/aadhaar")
async def screen_aadhaar(
    document: UploadFile = File(..., description="Aadhaar document image or PDF"),
    reference_face: Optional[UploadFile] = File(None, description="Optional reference face image"),
    offline_ekyc: Optional[UploadFile] = File(None, description="Optional offline eKYC XML or ZIP"),
    case_id: Optional[str] = Form(None, description="Optional case ID"),
    persist_artifacts: Optional[bool] = Form(False, description="Persist artifacts for debug/demo")
):
    global requests_served
    requests_served += 1
    if not document:
        raise HTTPException(status_code=400, detail="Document file is required")

    doc_bytes = await document.read()
    if len(doc_bytes) == 0:
        raise HTTPException(status_code=400, detail="Empty document file")

    ref_bytes = None
    if reference_face:
        ref_bytes = await reference_face.read()
        # Validate reference is image
        if len(ref_bytes) == 0:
            ref_bytes = None
        elif not reference_face.content_type or not reference_face.content_type.startswith("image/"):
            # also check extension
            if not reference_face.filename.lower().endswith((".jpg",".jpeg",".png")):
                # still try but note
                pass

    ekyc_bytes = None
    ekyc_name = None
    if offline_ekyc:
        ekyc_bytes = await offline_ekyc.read()
        ekyc_name = offline_ekyc.filename

    # Determine persist_artifacts boolean from form (might be string)
    if isinstance(persist_artifacts, str):
        persist_artifacts = persist_artifacts.lower() in ["true","1","yes"]

    result = run_pipeline(
        document_bytes=doc_bytes,
        filename=document.filename,
        reference_face_bytes=ref_bytes,
        ekyc_bytes=ekyc_bytes,
        ekyc_filename=ekyc_name,
        case_id=case_id,
        persist_artifacts=bool(persist_artifacts)
    )

    # Persist to storage
    try:
        repo.save(result["case_id"], result)
    except Exception as e:
        result["errors"].append({"stage":"storage","message": str(e)})

    return JSONResponse(content=result)

@app.get("/api/cases/{case_id}")
def get_case(case_id: str):
    data = repo.get(case_id)
    if not data:
        raise HTTPException(status_code=404, detail="Case not found")
    return data

@app.get("/api/cases")
def list_cases(limit: int = Query(20, ge=1, le=100)):
    return {"cases": repo.list_cases(limit=limit), "count": len(repo.list_cases(limit=limit))}

# Additional helper endpoints per spec (optional)
@app.post("/api/modules/aadhaar/validate-number")
def validate_number(number: str):
    from .services.number_validation import validate_aadhaar_number
    res = validate_aadhaar_number(number, number)
    return res

@app.post("/api/modules/aadhaar/qr")
async def qr_endpoint(document: UploadFile = File(...)):
    doc_bytes = await document.read()
    from .services.document_loader import load_document
    from .services.qr_analysis import detect_and_decode_qr
    from pathlib import Path
    import tempfile
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=Path(document.filename).suffix)
    tmp.write(doc_bytes)
    tmp.close()
    from pathlib import Path as P
    tmp_path = P(tmp.name)
    images, info, errs = load_document(tmp_path, doc_bytes)
    tmp_path.unlink(missing_ok=True)
    if not images:
        raise HTTPException(status_code=400, detail="Failed to load document")
    qr = detect_and_decode_qr(images)
    return qr

@app.post("/api/modules/aadhaar/forensics")
async def forensics_endpoint(document: UploadFile = File(...)):
    doc_bytes = await document.read()
    from .services.document_loader import load_document
    from .services.forensics import analyze_forensics
    from pathlib import Path
    import tempfile, cv2, numpy as np
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=Path(document.filename).suffix)
    tmp.write(doc_bytes)
    tmp.close()
    from pathlib import Path as P
    tmp_path = P(tmp.name)
    images, info, errs = load_document(tmp_path, doc_bytes)
    tmp_path.unlink(missing_ok=True)
    if not images:
        raise HTTPException(status_code=400, detail="Failed to load document")
    res = analyze_forensics(images[0]["image"])
    return res

@app.get("/")
def root():
    return {
        "service": "DAKSH P3 Aadhaar Screening",
        "module": settings.module,
        "docs": "/docs",
        "health": "/api/health",
        "screen": "POST /api/modules/aadhaar"
    }
