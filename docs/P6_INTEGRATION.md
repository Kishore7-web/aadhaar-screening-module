# P6 Integration Guide — DAKSH P3 Aadhaar Module

## Endpoint
**POST** `/api/modules/aadhaar`

### Request
`multipart/form-data`

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `document` | file (jpg/jpeg/png/pdf) | Yes | Aadhaar document scan/photo/PDF |
| `reference_face` | file (jpg/png) | No | Live/reference face for comparison |
| `offline_ekyc` | file (xml/zip) | No | UIDAI offline eKYC |
| `case_id` | string | No | Custom ID; auto-generated if missing (`CASE-XXXXXXXX`) |
| `persist_artifacts` | bool / string `"true"` | No | Save annotated crops for demo (`false` by default, HASH_ONLY) |

### Example Python
```python
import requests

url = "http://localhost:8000/api/modules/aadhaar"
files = {
  "document": open("samples/01_clean.png", "rb"),
  "reference_face": open("samples/ref_face_match.jpg", "rb")  # optional
}
data = {"case_id": "CASE-DEMO-001", "persist_artifacts": "true"}
res = requests.post(url, files=files, data=data)
print(res.json()["screening"]["status"])  # CLEAR | LOW_CONCERN | REVIEW | HIGH_REVIEW | INCONCLUSIVE
print(res.json()["scores"]["integrity_score"], res.json()["scores"]["evidence_coverage"])
```

### Example JavaScript
```js
const fd = new FormData();
fd.append('document', documentFile);
if (refFile) fd.append('reference_face', refFile);
if (ekycFile) fd.append('offline_ekyc', ekycFile);
fd.append('case_id', 'CASE-WEB-001');
const res = await fetch('http://localhost:8000/api/modules/aadhaar', {method:'POST', body:fd});
const json = await res.json();
console.log(json.screening.headline, json.scores.integrity_score);
```

### Example cURL
```bash
curl -X POST http://localhost:8000/api/modules/aadhaar \
  -F document=@samples/01_clean.png \
  -F reference_face=@samples/ref_face_match.jpg \
  -F persist_artifacts=true
```

## Response Contract (P3 JSON)
Top-level:
```json
{
  "schema_version": "1.0",
  "case_id": "CASE-AB12CD34",
  "document_type": "aadhaar",
  "document_variant": "physical",
  "module": "P3_AADHAAR",
  "module_version": "1.0.0",
  "module_status": "COMPLETE",
  "generated_at": "2026-09-20T...Z",
  "processing": {"started_at":"...", "completed_at":"...", "duration_ms":1234, "stages":[...]},
  "capabilities": {"ocr":true,"qr":true,"qr_signature":false,"photo":true,"face_comparison":true,"forensics":true,"offline_ekyc":false},
  "document": {"file_name":"...","file_type":"png","sha256":"...","page_count":1},
  "document_identification": {"result":"AADHAAR","confidence":0.85},
  "fields": {
    "name": {"value":"Aarav Kumar","raw_value":"Aarav Kumar","normalized_value":"Aarav Kumar","confidence":0.92,"confidence_basis":"OCR_ENGINE","status":"DETECTED","sources":[{"type":"OCR","confidence":0.92}],"consistency":"MATCH"},
    "dob": {...}, "gender": {...}, "aadhaar_number": {"value":"1234 5678 9012","masked_value":"XXXX XXXX 9012","status":"DETECTED"}, "address": {...}
  },
  "number_validation": {"format_status":"FORMAT_VALID","checksum_status":"CHECKSUM_VALID","checksum_message":"Mathematical/checksum validation passed."},
  "qr": {"status":"QR_PRESENT","decoded":true,"fields":{"name":"Aarav Kumar","yob":"2005"}},
  "qr_consistency": {"checked":true,"items":[{"field":"name","printed_value":"Aarav Kumar","qr_value":"Aarav Kumar","result":"MATCH"}],"overall":"MATCH"},
  "photo": {"status":"DETECTED","quality_label":"GOOD"},
  "biometric": {"status":"MATCH","similarity":0.84,"threshold":0.6,"model":"OpenCV-Haar+Histogram-v1"},
  "forensics": {"analyzed":true,"overall_label":"NO_SIGNIFICANT_SIGNAL","regions":[]},
  "metadata": {"editing_software_detected":false},
  "offline_ekyc": {"provided":false,"status":"NOT_PROVIDED","signature_status":"NOT_CONFIGURED"},
  "evidence": [{"evidence_id":"E-AAD-001","source":"OCR","category":"FIELD_EXTRACTION","finding":"Name extracted...","severity":"INFO","confidence":0.92,"confidence_basis":"OCR_ENGINE","group":"FIELD","independent_source":false}],
  "contradictions": [{"contradiction_id":"C-AAD-001","field":"dob","source_a":"OCR","value_a":"12/04/2005","source_b":"QR","value_b":"12/04/2004","severity":"HIGH"}],
  "evidence_relations": [{"relation_id":"R-AAD-001","type":"CORRELATED","evidence_ids":["E-AAD-001","E-AAD-002"],"description":"OCR-derived fields share same source"}],
  "scores": {"integrity_score":92,"evidence_coverage":88,"coverage_sufficient":true,"breakdown":{...}},
  "screening": {"status":"CLEAR","headline":"Document screening completed — no significant concerns detected.","reasons":[{"text":"Available evidence is mostly consistent...","evidence_ids":["E-AAD-001"]}],"recommended_action":"No immediate action...","next_steps":[...],"limitations":[...]},
  "artifacts": {"original_hash":"...","items":[]},
  "audit": {"case_id":"...","document_hash":"...","manifest_hash":"...","chain_event_id":"EVT-...","chain_event_hash":"...","chain_verified":true,"blockchain_status":"NOT_CONFIGURED"},
  "privacy": {"masked_aadhaar":"XXXX XXXX 9012","storage_mode":"HASH_ONLY"},
  "errors": []
}
```

### Key Enums
- `screening.status`: `CLEAR` (no major concern, coverage sufficient) | `LOW_CONCERN` (only low) | `REVIEW` (meaningful inconsistency) | `HIGH_REVIEW` (multiple independent families) | `INCONCLUSIVE` (coverage < ~30% or very blurry). `INCONCLUSIVE` is NOT fake.
- `number_validation.checksum_status`: `CHECKSUM_VALID` (“Mathematical/checksum validation passed.”) | `CHECKSUM_INVALID` | `MASKED` (not checked) | `NOT_CHECKED`
- `qr.status`: `QR_PRESENT` | `QR_NOT_PRESENT` | `QR_UNREADABLE`
- `photo.status`: `DETECTED` | `NOT_FOUND` | `LOW_QUALITY` | `AMBIGUOUS`
- `biometric.status`: `MATCH` | `MISMATCH` | `LOW_CONFIDENCE` | `FACE_NOT_FOUND` | `MULTIPLE_FACES` | `NOT_CHECKED` | `NOT_AVAILABLE`
- `forensics.overall_label`: `NO_SIGNIFICANT_SIGNAL` | `LOW_SIGNAL` | `SUSPICIOUS`

### Evidence Provenance
Every field preserves `sources: [{type:"OCR", confidence:0.92}]` and `consistency: MATCH|MISMATCH`. Evidence items have `evidence_id`, `group`, `independent_source` (OCR-derived fields are `false`; QR, forensics, biometric are `true`). Correlation handling: OCR fields correlated → not double-counted; independent groups (QR + forensic on same DOB) increase review priority.

### Hash & Audit
- `document.sha256` = SHA-256 of original bytes
- `audit.manifest_hash` = SHA-256(canonical JSON of evidence+scores+screening)
- `audit.chain_event_hash = SHA256(previous_hash + canonical(event))` chain verified via `GET /api/health/details` → `audit_status.verified`

### P6 Consumption
P6 can compare fields across modules:
```python
# Example cross-document check (P6 layer)
if aadhaar_response["fields"]["name"]["value"].lower() == pan_response["fields"]["name"]["value"].lower():
    pass  # name consistent across Aadhaar ↔ PAN
# Use `audit.document_hash` for chaining, `evidence` for audit trail, `contradictions` for UI.
```

### Statuses That Are NOT Failures
- `NOT_CHECKED` / `NOT_AVAILABLE` / `NOT_PROVIDED` / `NOT_CONFIGURED` mean optional evidence absent, NOT failed. Do not penalize score for absence.

### Limits
- Integrity Score is NOT fraud probability; 100 = very low concern from available evidence, 0 = very high concern.
- “Official UIDAI authentication was not performed.” Always show limitations.
- Face result wording: “Face comparison is consistent/not sufficiently consistent with the supplied reference image.” Not “Identity verified.”

## Other Endpoints
- `GET /api/health` → service/module versions, components
- `GET /api/health/details` → platform, uptime, storage, model status, audit chain verification
- `GET /api/cases/{case_id}` → retrieve stored JSON
- `GET /api/cases?limit=20` → list summaries
- `POST /api/modules/aadhaar/validate-number` → number only
- `POST /api/modules/aadhaar/qr` / `forensics` → helper diagnostics

## Security Notes for P6
- Validate `document.size` before forwarding (10 MB limit).
- Masked Aadhaar (`privacy.masked_aadhaar`) is safe to log; never log `fields.aadhaar_number.value` full if present.
- Chain is tamper-evident; store `manifest_hash` externally if needed.
- Blockchain status will be `NOT_CONFIGURED` in MVP; do not block on it.
