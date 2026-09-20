# DAKSH — P3 Aadhaar Screening
### Document Authentication & Knowledge-based Screening Hub
**SIH 2026 | Problem Statement 26188 | Ministry of Home Affairs – SSB, Police II Division | Theme: Blockchain & Cybersecurity**

AI-assisted Aadhaar document screening system that analyzes Aadhaar documents using multiple evidence sources and produces a transparent 0–100 Document Integrity Score, evidence coverage, review priority, human-readable explanation, and tamper-evident audit trail. **This is NOT an official UIDAI authentication service.**

> **Core principle:** Evidence → Validation → Consistency → Forensics → Biometric Checks → Evidence Fusion → Review Priority → Explanation

![Status](https://img.shields.io/badge/Build-COMPLETE-green) ![Schema](https://img.shields.io/badge/Schema-1.0-blue) ![Python](https://img.shields.io/badge/Python-3.13-blue)

---

## Features (P3 Complete)
- **Secure intake:** JPG/PNG/PDF, size/MIME/magic/filename sanitization, ZIP traversal protection
- **Document loader:** PDF page rendering (PyMuPDF, 5-page limit), SHA-256, image quality (blur, glare)
- **Orientation:** 0/90/180/270 via OCR keyword scoring
- **OCR:** RapidOCR (onnxruntime) with fallback, confidence + bounding boxes
- **Field extraction + provenance:** Name, DOB, Gender, Aadhaar number (masked-aware), Address — each with raw/normalized/masked, confidence, sources, bbox
- **Aadhaar number:** Verhoeff checksum, masked detection (`XXXX XXXX 9012`), OCR ambiguity flag
- **QR:** OpenCV QRCodeDetector, field parsing (uid/name/yob/gender/pc etc.), printed↔QR consistency (exact/year/masked handling)
- **Photo/Face:** Haar detection, quality, optional reference face comparison (cosine on histogram embedding, SFace-compatible fallback)
- **Forensics:** local noise/sharpness variance, ELA-like recompression, hotspot regions + annotated artifacts
- **Metadata:** EXIF, software tags
- **Offline e-KYC:** safe XML/ZIP parsing (20-file/5 MB limit), three-source consistency, signature adapter (`NOT_CONFIGURED` without cert)
- **Evidence engine:** `E-AAD-001` with severity, confidence_basis, group, independent_source
- **Contradiction + correlation:** `C-AAD-001` with explanations, `R-AAD-001` correlated vs independent
- **Scoring:** Integrity 0–100 (weighted penalties) + Coverage 0–100 (how much evidence was available)
- **Screening:** `CLEAR|LOW_CONCERN|REVIEW|HIGH_REVIEW|INCONCLUSIVE` deterministic + human explanation + next steps
- **Audit:** SHA-256 chain (`previous_hash + canonical(event)`), blockchain adapter (`NOT_CONFIGURED` fallback)
- **Storage:** LocalRepository (fallback) + MongoRepository adapter
- **Frontend:** React/Vite professional dashboard (upload → progress → integrity/coverage hero → field table → QR comparison → face → forensics → evidence → audit → P6 JSON)
- **Synthetic data:** 20 controlled samples (watermarked `SYNTHETIC TEST DOCUMENT • NOT A REAL AADHAAR`) + face refs + manifest
- **Tests:** pytest covering number, OCR, doc ID, QR, face, forensics, scoring, API, security

---

## Architecture
See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for pipeline, diagram, and P6 contract.

```
USER → React → FastAPI → SecureInput → Loader → Quality → OCR → Fields → Number → QR → Photo → Face → Metadata → Forensics → eKYC → Evidence → Contradictions → Scoring → Explanation → Audit → JSON → Storage → UI
```

## Folder Structure
```
daksh-aadhaar/
  backend/
    app/
      main.py            # FastAPI, health, /api/modules/aadhaar
      config.py
      models/schemas.py  # Pydantic contract (schema_version 1.0)
      services/          # pipeline, ocr_adapter, qr_analysis, forensics, etc.
      utils/             # hashing, verhoeff, image_utils
  frontend/
    src/
      App.jsx            # Dashboard
      components/        # Upload, Result, Evidence, QR, Face, Forensic, Audit
      services/api.js
  scripts/
    generate_test_documents.py  # 20 synthetic samples
    setup_models.py
  tests/                 # pytest suites
  docs/
    ARCHITECTURE.md
    P6_INTEGRATION.md
    TESTING.md
    STATUS.md
  samples/               # generated synthetic images + manifest
  data/
    artifacts/           # case JSONs, annotated crops (when persist_artifacts=true)
    audit_chain.jsonl    # tamper-evident chain
  models/                # optional SFace/YuNet ONNX (fallback if absent)
  README.md
  requirements.txt
  .env.example
```

## Quick Start (Windows / PowerShell)

### Prerequisites
- Python 3.10+ (3.13 tested)
- Node 20+
- Git

### Backend
```powershell
cd daksh-aadhaar
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
# or: pip install -r backend/requirements.txt

# check models
python scripts/setup_models.py

# generate synthetic samples (first time)
python scripts/generate_test_documents.py

# run server
uvicorn backend.app.main:app --reload --port 8000
# or from project root:
# python -m uvicorn backend.app.main:app --reload --port 8000
```
Swagger: http://localhost:8000/docs

### Frontend
```powershell
cd frontend
npm install
npm run dev
# open http://localhost:5173
# production build
npm run build
npm run preview
```

### Tests
```powershell
# backend dir
pytest -q
pytest tests/test_api.py -v
```

### API Example
```bash
curl -X POST http://localhost:8000/api/modules/aadhaar -F document=@samples/01_clean.png
# with reference face
curl -X POST http://localhost:8000/api/modules/aadhaar -F document=@samples/01_clean.png -F reference_face=@samples/ref_face_match.jpg -F persist_artifacts=true
```

---

## Synthetic Data
```bash
python scripts/generate_test_documents.py
```
Creates `samples/01_clean.png` … `20_multi_source_contradiction.png` (+ `.jpg` + `.json` + `manifest.json`), each watermarked. Expected outcomes in `samples/manifest.json`. No real PII.

## Model Setup
- **RapidOCR** auto-downloads ONNX models on first use (no manual step).
- **Haar cascade** ships with OpenCV.
- **Optional SFace/YuNet**: download `face_detection_yunet_2023mar.onnx` and `face_recognition_sface_2021dec.onnx` into `models/` to enable higher-accuracy face (fallback is Haar+Histogram if absent).
- **Tesseract not required** (RapidOCR primary).
- **MongoDB optional** (falls back to local JSON).
- **Blockchain optional** (local hash chain fallback).

`python scripts/setup_models.py` prints status.

## API Documentation
Interactive Swagger at `/docs`. See [docs/P6_INTEGRATION.md](docs/P6_INTEGRATION.md) for endpoint, schema, example Python/JS, enums, and cross-document (Aadhaar ↔ PAN etc.) guidance for P6.

## Security / Privacy
- SHA-256 hashes for document/manifest; masked Aadhaar `XXXX XXXX 9012`; chain contains only hashes, not raw PII.
- Temporary files isolated and cleaned; ZIP extraction bounded.
- Logs mask identifiers (`********9012`).
- Watermark on synthetic docs; no fake UIDAI verification claims.

## Limitations
- Not official UIDAI authentication; secondary authorized verification recommended.
- Face simple model — not biometric identity proof.
- QR signature `NOT_CONFIGURED` without cert.
- Forensics is heuristic supporting evidence.

## Troubleshooting
- `ModuleNotFoundError: rapidocr` → `pip install rapidocr_onnxruntime onnxruntime`
- `Port 8000 in use` → `uvicorn ... --port 8001` and update Vite proxy in `frontend/vite.config.js`
- Frontend `ECONNREFUSED` → ensure backend running; proxy targets `http://localhost:8000`
- Low OCR accuracy → use generated clean PNG (not heavily blurred JPG); ensure lighting

---

## Team
- P1 Passport, P2 Visa, **P3 Aadhaar (this module)**, P4 PAN, P5 Driving Licence, P6 Common Intelligence & Integration

## License
Prototype for SIH 2026 evaluation.

