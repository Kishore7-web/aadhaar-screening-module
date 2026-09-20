# DAKSH P3 Aadhaar — Architecture

## Overview
```
USER → React (Vite) → FastAPI (app/main.py) → Secure Input → Document Loader (PyMuPDF / OpenCV)
→ Quality → OCR (RapidOCR) → Field Extraction → Number Validation (Verhoeff)
→ QR Analysis (OpenCV) → Photo Detection (Haar) → Face Comparison (Haar+Histogram)
→ Metadata → Forensics (Noise/Sharpness/ELA-like) → Offline eKYC (optional, XML/ZIP)
→ Crypto Adapter (NOT_CONFIGURED fallback) → Evidence Engine → Contradiction Engine
→ Scoring (Integrity 0–100 + Coverage 0–100) → Explanation → Audit Hash Chain → JSON (P6)
→ Storage (LocalRepository + MongoRepository fallback) → React rendering
```

## Component Diagram
- **Secure Input** (`secure_input.py`): validates extension, MIME, magic bytes, size, sanitizes filename, protects ZIP path traversal.
- **Document Loader** (`document_loader.py`): renders PDFs via PyMuPDF at 200 DPI, decodes images via OpenCV/Pillow, limits pages to 5.
- **OCR Adapter** (`ocr_adapter.py`): abstraction `OCREngine`; primary `RapidOCREngine` (onnxruntime), fallback that returns NOT_AVAILABLE. Returns text, confidence, bounding boxes.
- **Orientation** (`orientation.py`): tests 0° vs 180° (and 90/270 if low confidence) using OCR keyword scoring.
- **Document Identification** (`doc_identification.py`): heuristic scoring of keywords (aadhaar, uidai, govt), number pattern, QR presence, DOB/gender cues.
- **Field Extraction** (`field_extraction.py`): regex for Name, DOB, Gender, Aadhaar number (masked-aware), Address; preserves provenance (raw, normalized, masked, confidence, bbox).
- **Number Validation** (`number_validation.py` + `verhoeff.py`): Verhoeff checksum, masked detection, OCR ambiguity flag.
- **QR Analysis** (`qr_analysis.py`): OpenCV `QRCodeDetector` detect+decode, parses XML fields (`uid`, `name`, `yob`, `gender`, `pc` etc.), compares printed ↔ QR with exact vs year-only vs masked handling.
- **Photo Detection** (`photo_detection.py`): Haar cascade frontalface, quality via Laplacian variance.
- **Face Analysis** (`face_analysis.py`): Haar + histogram embedding (fallback for SFace), cosine similarity, thresholds 0.75 MATCH / 0.60 LOW_CONFIDENCE.
- **Metadata** (`metadata_analysis.py`): PIL EXIF, software tags.
- **Forensics** (`forensics.py`): local variance, sharpness inconsistency, ELA-like recompression via JPEG diff 90 quality, contour detection for hotspot.
- **eKYC Parser** (`ekyc_parser.py`): safe ZIP extraction with traversal protection, XML parsing for `UidData`/`Poi`/`Poa`, fields extraction.
- **Crypto Verifier** (`crypto_verifier.py`): adapter returning `NOT_CONFIGURED` when cert not found.
- **Evidence Engine** (`evidence_engine.py`): every finding → `E-AAD-xxx` with source, category, severity, confidence_basis, group, independent_source.
- **Contradiction Engine** (`contradiction_engine.py`): builds `C-AAD-xxx` from QR mismatches and three-source checks; relations for correlated vs independent.
- **Scoring Engine** (`scoring_engine.py`): deterministic weights (Quality 10, Field 15, Number 10, QR 20, Biometric 20, Forensics 15, Metadata 5, DocID 5) subtract penalties, correlation-aware cap, coverage computed from 6 required + optional families.
- **Explanation Engine** (`explanation_engine.py`): maps scores to CLEAR/LOW_CONCERN/REVIEW/HIGH_REVIEW/INCONCLUSIVE, reasons map to evidence_ids, recommended action per status.
- **Pipeline** (`pipeline.py`): orchestrates all stages, graceful error handling (stage failure → error list, continue), builds standardized JSON.
- **Audit Service** (`audit_service.py`): SHA-256 chain, canonical JSON, `previous_hash + canonical -> event_hash`, append-only `data/audit_chain.jsonl`, `verify_chain()`.
- **Blockchain Adapter** (`blockchain_adapter.py`): `NOT_CONFIGURED` fallback, future RPC anchoring.
- **Storage** (`storage.py`): `LocalRepository` (JSON files under `data/artifacts/cases`) and `MongoRepository` (attempt `pymongo`, fallback).
- **FastAPI** (`main.py`): `/api/health`, `/api/health/details`, `POST /api/modules/aadhaar`, `GET /api/cases/{id}`, `/api/cases`.

## Data Flow
1. Multipart upload → `secure_input.validate_and_save_document` → temp file + SHA-256.
2. `load_document` → images array + `doc_loader_info`.
3. `quality` metrics → blur via Laplacian variance.
4. `ocr_adapter.ocr_images` → `ocr_text`, confidence.
5. `orientation` corrects images if needed (re-OCR if rotated).
6. Parallel: QR, photo, metadata, forensics start from first image.
7. Field extraction + number validation consume OCR text.
8. QR consistency merges OCR fields and QR fields.
9. eKYC parsed separately, evidence adds three-source contradiction.
10. Evidence → contradictions → relations → scores → screening → audit.

## P6 Integration
Response JSON follows `schemas.py` `AadhaarScreeningResponse` with versioned `schema_version:1.0`. Fields include provenance (`sources`, `confidence_basis`), evidence IDs, audit hashes. React never computes score; it renders backend JSON.

## Failure / Fallback
- OCR fails → continue QR/forensics with `NOT_AVAILABLE`.
- Mongo fails → local fallback.
- Blockchain fails → local hash chain, status `NOT_CONFIGURED`.
- One stage exception → `errors[]`, stage marked ERROR, pipeline continues.
- Tesseract/EasyOCR missing → RapidOCR primary; if all fail → coverage reduced → INCONCLUSIVE (no fake data).

## Security
- SHA-256 for document/manifest/report.
- Filename sanitization, path traversal block, ZIP traversal block, size limits, temp isolation, cleanup.
- Privacy: masked Aadhaar (`XXXX XXXX 9012`), no raw PII on chain, logs mask identifiers.
- CORS configured.

## Performance
- Lazy model load (RapidOCR loaded once), cache, image resize `max_dim 1200`, PDF page limit 5, ZIP size limit 5 MB, bounded image dimensions.

