# Testing — DAKSH P3

## Run
```bash
# backend
cd backend
pytest -q
pytest tests/test_api.py -v
pytest tests/test_number_validation.py -v

# frontend build
cd frontend
npm install
npm run build
```

## Categories (pytest)
- **Number**: `test_number_validation.py` — valid 12-digit, invalid length, non-numeric, checksum valid/invalid, masked, OCR ambiguity (O/0)
- **OCR**: `test_ocr.py` — normal text, blurry/low confidence, empty image handling
- **Orientation**: heuristic via keyword scoring; tested manually via rotated sample `11_rotated` (expects correction to 90°)
- **Document identification**: `test_document.py` — Aadhaar detected, unsupported, low confidence
- **QR**: `test_qr.py` — detected/decoded, not present, printed↔QR match/mismatch
- **Face**: `test_face.py` — match (same synthetic color), mismatch (different), no reference → NOT_CHECKED, no face → FACE_NOT_FOUND, multiple faces (via Haar multiple detections)
- **Forensics**: `test_forensics.py` — clean (NO_SIGNIFICANT_SIGNAL), blurry, recompressed (ELA-like)
- **Evidence / Contradiction**: covered via scoring tests and API integration (evidence IDs unique, provenance, grouped)
- **Scoring**: `test_scoring.py` — deterministic (same input → same score), clean case ≥80, one anomaly → REVIEW-like penalty, multiple → high penalty, low coverage → INCONCLUSIVE, correlation cap (blur reduces field penalty)
- **API**: `test_api.py` — health, health/details, upload success, invalid file, missing file, optional face, optional eKYC, case retrieval, graceful failure
- **Security**: `test_security.py` — path traversal filename sanitized, oversized file rejected, MIME/magic mismatch, unsafe ZIP traversal blocked, corrupted PDF

## Synthetic Cases (samples/)
Generated via `scripts/generate_test_documents.py` (20 variants):

| ID | Variant | Expected Status | Key Evidence |
|----|---------|-----------------|--------------|
| 01_clean | clean | CLEAR | None |
| 02_modified_dob | DOB tamper | REVIEW | QR contradiction + forensic anomaly |
| 03_modified_name | name | REVIEW | QR contradiction |
| 04_modified_number | number | REVIEW | CHECKSUM_INVALID |
| 05_modified_gender | gender | REVIEW | QR mismatch |
| 06_modified_address | address | LOW_CONCERN | minor |
| 07_replaced_photo | photo | REVIEW | forensic + photo quality |
| 08_multiple | multiple (dob+name) | HIGH_REVIEW | multiple independent |
| 09_face_mismatch | clean + different ref | REVIEW | MISMATCH |
| 10_blurry | blur | INCONCLUSIVE | LOW_QUALITY, low coverage |
| 11_rotated | 90° | CLEAR after correction | orientation |
| 12_screenshot_recompressed | recompress | LOW_CONCERN | recompression signal |
| 13_qr_contradiction | dob | REVIEW | QR mismatch |
| 14_masked | masked | CLEAR (masked) | MASKED |
| 15_missing_qr | no QR | LOW_CONCERN/CLEAR | QR_NOT_PRESENT |
| 16_missing_photo | no photo | REVIEW | PHOTO_NOT_FOUND |
| 17_low_ocr | blur+recompress | INCONCLUSIVE | low OCR |
| 18_partial_document | cropped half | INCONCLUSIVE | low coverage |
| 19_module_failure | corrupted jpg | PARTIAL | error handling |
| 20_multi_source | multiple+three-source | HIGH_REVIEW | three-source mismatch |

Each sample has `samples/<id>.json` with `expected_evidence` and `expected_status`. The pipeline processes each normally—no hardcoded score.

## Manual Validation (pre-demo checklist)
```bash
# start backend
uvicorn app.main:app --reload --port 8000
# in another terminal
curl http://localhost:8000/api/health
curl -F document=@samples/01_clean.png http://localhost:8000/api/modules/aadhaar | jq .screening.status  # expect CLEAR
curl -F document=@samples/02_modified_dob.png http://localhost:8000/api/modules/aadhaar | jq .contradictions  # expect dob mismatch
curl -F document=@samples/14_masked.png http://localhost:8000/api/modules/aadhaar | jq .number_validation   # expect MASKED
curl -F document=@samples/10_blurry.png http://localhost:8000/api/modules/aadhaar | jq .scores.evidence_coverage  # expect low
```

## Performance
- Lazy OCR load, resize max 1200, PDF max 5 pages, ZIP max 5 MB / 20 files.
- Typical screening: 1–3 s for 1000×650 image on laptop (including OCR, QR, forensics).
- Frontend proxy to backend via Vite `/api` → no CORS issues.

## Known Limits
- OCR accuracy depends on image quality; handwritten documents not supported.
- Face comparison uses lightweight Haar+Histogram fallback (not SFace-level accuracy) unless YUnet/SFace ONNX provided in `models/`.
- QR signature verification `NOT_CONFIGURED` without UIDAI cert—parsing only.
- Forensics heuristics are supporting evidence, not proof of manipulation.
