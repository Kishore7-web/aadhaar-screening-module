from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional, Dict, Any, Literal
from datetime import datetime
from enum import Enum

# Enums
class DocumentType(str, Enum):
    aadhaar = "aadhaar"
    unknown = "unknown"

class ModuleStatus(str, Enum):
    COMPLETE = "COMPLETE"
    PARTIAL = "PARTIAL"
    FAILED = "FAILED"

class DocIdentification(str, Enum):
    AADHAAR = "AADHAAR"
    NOT_CONFIDENT = "NOT_CONFIDENT"
    UNSUPPORTED_DOCUMENT = "UNSUPPORTED_DOCUMENT"

class Variant(str, Enum):
    physical = "physical"
    pvc = "pvc"
    letter = "letter"
    e_aadhaar = "e_aadhaar"
    masked = "masked"
    scan = "scan"
    photo = "photo"
    screenshot = "screenshot"
    unknown = "unknown"

class FieldStatus(str, Enum):
    DETECTED = "DETECTED"
    NOT_FOUND = "NOT_FOUND"
    LOW_CONFIDENCE = "LOW_CONFIDENCE"
    PARTIAL = "PARTIAL"
    MASKED = "MASKED"
    INVALID = "INVALID"
    NOT_APPLICABLE = "NOT_APPLICABLE"

class NumberValidationStatus(str, Enum):
    FORMAT_VALID = "FORMAT_VALID"
    CHECKSUM_VALID = "CHECKSUM_VALID"
    CHECKSUM_INVALID = "CHECKSUM_INVALID"
    FORMAT_INVALID = "FORMAT_INVALID"
    MASKED = "MASKED"
    NOT_CHECKED = "NOT_CHECKED"

class QRStatus(str, Enum):
    QR_PRESENT = "QR_PRESENT"
    QR_NOT_PRESENT = "QR_NOT_PRESENT"
    QR_UNREADABLE = "QR_UNREADABLE"
    DECODED = "DECODED"

class PhotoStatus(str, Enum):
    DETECTED = "DETECTED"
    NOT_FOUND = "NOT_FOUND"
    LOW_QUALITY = "LOW_QUALITY"
    AMBIGUOUS = "AMBIGUOUS"

class FaceStatus(str, Enum):
    MATCH = "MATCH"
    MISMATCH = "MISMATCH"
    LOW_CONFIDENCE = "LOW_CONFIDENCE"
    NOT_CHECKED = "NOT_CHECKED"
    NOT_AVAILABLE = "NOT_AVAILABLE"
    FACE_NOT_FOUND = "FACE_NOT_FOUND"
    MULTIPLE_FACES = "MULTIPLE_FACES"

class CryptoStatus(str, Enum):
    VERIFIED = "VERIFIED"
    INVALID_SIGNATURE = "INVALID_SIGNATURE"
    CERTIFICATE_ERROR = "CERTIFICATE_ERROR"
    UNSUPPORTED = "UNSUPPORTED"
    NOT_CONFIGURED = "NOT_CONFIGURED"
    NOT_CHECKED = "NOT_CHECKED"

class ScreeningStatus(str, Enum):
    CLEAR = "CLEAR"
    LOW_CONCERN = "LOW_CONCERN"
    REVIEW = "REVIEW"
    HIGH_REVIEW = "HIGH_REVIEW"
    INCONCLUSIVE = "INCONCLUSIVE"

class Severity(str, Enum):
    INFO = "INFO"
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"

# Sub models
class SourceRef(BaseModel):
    type: str = Field(description="Source type: OCR, QR, EKYC etc")
    confidence: Optional[float] = None
    page: Optional[int] = None

class FieldProvenance(BaseModel):
    value: Optional[str] = None
    raw_value: Optional[str] = None
    normalized_value: Optional[str] = None
    masked_value: Optional[str] = None
    confidence: Optional[float] = None
    confidence_basis: Optional[str] = None
    status: FieldStatus = FieldStatus.NOT_FOUND
    sources: List[SourceRef] = []
    bounding_box: Optional[List[int]] = None  # [x,y,w,h]
    page: Optional[int] = None
    notes: Optional[str] = None
    consistency: Optional[str] = None

class ProcessingStage(BaseModel):
    name: str
    status: str
    duration_ms: Optional[int] = None
    notes: Optional[str] = None

class ProcessingInfo(BaseModel):
    started_at: str
    completed_at: str
    duration_ms: int
    pipeline_stage: str = "COMPLETE"
    build_stage_label: str = "COMPLETE"
    stages: List[ProcessingStage] = []
    pending_components: List[str] = []
    optional_inputs: List[str] = []
    notes: List[str] = []

class Capabilities(BaseModel):
    document_identification: bool = True
    quality_analysis: bool = True
    orientation_analysis: bool = True
    security_checks: bool = True
    ocr: bool = True
    number_validation: bool = True
    qr: bool = True
    qr_signature: bool = False
    photo: bool = True
    face_reference: bool = False
    face_comparison: bool = False
    forensics: bool = True
    metadata: bool = True
    offline_ekyc: bool = False

class DocumentInfo(BaseModel):
    file_name: Optional[str] = None
    file_type: Optional[str] = None
    file_size_bytes: Optional[int] = None
    mime_type: Optional[str] = None
    page_count: int = 1
    pages_analyzed: int = 1
    sha256: Optional[str] = None
    load_duration_ms: Optional[int] = None
    storage_mode: str = "HASH_ONLY"

class DocumentSecurity(BaseModel):
    file_size_check: str = "PASS"
    mime_check: str = "PASS"
    extension_check: str = "PASS"
    magic_byte_check: str = "PASS"
    filename_sanitized: bool = True
    path_traversal_check: str = "PASS"
    corrupted_check: str = "PASS"
    pdf_check: Optional[str] = None
    zip_check: Optional[str] = None
    notes: List[str] = []

class DocumentIdentification(BaseModel):
    result: DocIdentification = DocIdentification.NOT_CONFIDENT
    confidence: Optional[float] = None
    confidence_basis: str = "HEURISTIC"
    variant: Variant = Variant.unknown
    signals: List[str] = []
    keywords_found: List[str] = []
    notes: Optional[str] = None

class PageAnalysis(BaseModel):
    page_number: int
    width: int
    height: int
    dpi_estimate: Optional[int] = None
    text_layer_present: bool = False
    notes: Optional[str] = None

class QualityMetrics(BaseModel):
    overall_score: Optional[float] = None  # 0-100
    overall_label: str = "UNKNOWN"  # GOOD, MEDIUM, POOR
    blur_score: Optional[float] = None
    blur_label: Optional[str] = None
    brightness: Optional[float] = None
    contrast: Optional[float] = None
    glare_detected: bool = False
    is_blurry: bool = False
    is_low_quality: bool = False
    notes: List[str] = []

class OrientationInfo(BaseModel):
    applied_rotation: int = 0  # 0,90,180,270
    detected_rotation: Optional[int] = None
    candidate_scores: Dict[str, float] = {}
    confidence: Optional[float] = None
    method: str = "HEURISTIC"
    ambiguous: bool = False
    notes: Optional[str] = None

class NumberValidation(BaseModel):
    raw_candidate: Optional[str] = None
    normalized: Optional[str] = None
    masked_value: Optional[str] = None
    is_masked: bool = False
    format_status: NumberValidationStatus = NumberValidationStatus.NOT_CHECKED
    checksum_status: NumberValidationStatus = NumberValidationStatus.NOT_CHECKED
    checksum_message: Optional[str] = None
    ocr_ambiguities_considered: bool = False
    notes: Optional[str] = None

class QRInfo(BaseModel):
    status: str = "QR_NOT_PRESENT"  # QR_PRESENT etc
    decoded: bool = False
    data_raw: Optional[str] = None
    data_truncated: Optional[str] = None
    fields: Dict[str, Any] = {}
    bounding_box: Optional[List[int]] = None
    page: Optional[int] = None
    decode_time_ms: Optional[int] = None
    notes: Optional[str] = None

class QRConsistencyItem(BaseModel):
    field: str
    printed_value: Optional[str] = None
    qr_value: Optional[str] = None
    result: str = "NOT_CHECKED" # MATCH, MISMATCH, NOT_AVAILABLE
    severity: Optional[str] = None
    notes: Optional[str] = None

class QRConsistency(BaseModel):
    checked: bool = False
    items: List[QRConsistencyItem] = []
    overall: str = "NOT_CHECKED"
    mismatches: int = 0

class PhotoInfo(BaseModel):
    status: PhotoStatus = PhotoStatus.NOT_FOUND
    bounding_box: Optional[List[int]] = None
    page: Optional[int] = None
    quality_score: Optional[float] = None
    quality_label: Optional[str] = None
    has_crop: bool = False
    notes: Optional[str] = None

class BiometricInfo(BaseModel):
    status: FaceStatus = FaceStatus.NOT_CHECKED
    has_reference: bool = False
    reference_face_found: bool = False
    document_face_found: bool = False
    similarity: Optional[float] = None
    distance: Optional[float] = None
    threshold: float = 0.6
    model: str = "OpenCV-Haarcascade+SFace-fallback"
    model_version: str = "1.0"
    metric: str = "cosine"
    quality: Optional[str] = None
    message: Optional[str] = None
    notes: Optional[str] = None

class ForensicRegion(BaseModel):
    region_id: str
    reason: str
    severity: Severity = Severity.LOW
    confidence: Optional[float] = None
    confidence_basis: str = "HEURISTIC"
    method: str
    bounding_box: Optional[List[int]] = None
    evidence_id: Optional[str] = None
    page: Optional[int] = None

class ForensicsInfo(BaseModel):
    analyzed: bool = True
    signals: List[str] = []
    regions: List[ForensicRegion] = []
    ela_score: Optional[float] = None
    noise_score: Optional[float] = None
    sharpness_variance: Optional[float] = None
    recompression_detected: bool = False
    overall_label: str = "NO_SIGNIFICANT_SIGNAL" # or SUSPICIOUS
    notes: Optional[str] = None

class MetadataInfo(BaseModel):
    exif: Dict[str, Any] = {}
    software_tags: List[str] = []
    creation_metadata: Optional[str] = None
    dimensions: Optional[str] = None
    file_type: Optional[str] = None
    signals: List[str] = []
    editing_software_detected: bool = False
    notes: Optional[str] = None

class OfflineEkycInfo(BaseModel):
    provided: bool = False
    status: str = "NOT_PROVIDED" # PARSED, FAILED, NOT_PROVIDED
    fields: Dict[str, Any] = {}
    signature_status: CryptoStatus = CryptoStatus.NOT_CHECKED
    signature_message: Optional[str] = None
    consistency: Optional[Dict[str, Any]] = None
    notes: Optional[str] = None

class EvidenceItem(BaseModel):
    evidence_id: str
    source: str
    category: str
    finding: str
    severity: Severity
    confidence: Optional[float] = None
    confidence_basis: str = "HEURISTIC"
    group: Optional[str] = None
    independent_source: bool = True
    region: Optional[str] = None
    artifact: Optional[str] = None
    data: Optional[Dict[str, Any]] = None

class ContradictionItem(BaseModel):
    contradiction_id: str
    field: str
    source_a: str
    value_a: Optional[str] = None
    source_b: str
    value_b: Optional[str] = None
    severity: Severity
    confidence: Optional[float] = None
    description: str
    possible_explanations: List[str] = []
    evidence_ids: List[str] = []
    group: Optional[str] = None

class EvidenceRelation(BaseModel):
    relation_id: str
    type: str  # CORRELATED, INDEPENDENT, DERIVED
    evidence_ids: List[str]
    description: str

class Scores(BaseModel):
    integrity_score: Optional[int] = None
    evidence_coverage: int = 0
    coverage_sufficient: bool = False
    scoring_model_version: str = "1.0"
    breakdown: Dict[str, Any] = {}
    capped_due_to_correlation: bool = False
    notes: Optional[str] = None

class ScreeningReason(BaseModel):
    text: str
    evidence_ids: List[str] = []

class ScreeningInfo(BaseModel):
    status: ScreeningStatus = ScreeningStatus.INCONCLUSIVE
    headline: str = ""
    reasons: List[ScreeningReason] = []
    recommended_action: str = ""
    next_steps: List[str] = []
    limitations: List[str] = []
    evidence_ids: List[str] = []

class ArtifactItem(BaseModel):
    type: str
    file_name: Optional[str] = None
    path: Optional[str] = None
    hash: Optional[str] = None
    available: bool = False
    page: Optional[int] = None

class ArtifactsInfo(BaseModel):
    original_hash: Optional[str] = None
    items: List[ArtifactItem] = []
    report_available: bool = False

class AuditInfo(BaseModel):
    case_id: str
    document_hash: Optional[str] = None
    manifest_hash: Optional[str] = None
    report_hash: Optional[str] = None
    chain_event_id: Optional[str] = None
    chain_event_hash: Optional[str] = None
    previous_hash: Optional[str] = None
    chain_verified: bool = True
    blockchain_status: str = "NOT_CONFIGURED"
    blockchain_tx: Optional[str] = None
    timestamp: Optional[str] = None
    notes: Optional[str] = None

class PrivacyInfo(BaseModel):
    masked_aadhaar: Optional[str] = None
    pii_stored: bool = False
    storage_mode: str = "HASH_ONLY"
    retention_note: str = "Raw document not persisted by default."

# Main contract
class AadhaarScreeningResponse(BaseModel):
    model_config = ConfigDict(extra="allow")
    schema_version: str = "1.0"
    case_id: str
    document_type: str = "aadhaar"
    document_variant: str = "unknown"
    module: str = "P3_AADHAAR"
    module_version: str = "1.0.0"
    module_status: ModuleStatus = ModuleStatus.COMPLETE
    generated_at: str

    processing: ProcessingInfo
    capabilities: Capabilities
    document: DocumentInfo
    document_security: DocumentSecurity
    document_identification: DocumentIdentification
    page_analyses: List[PageAnalysis] = []
    quality: QualityMetrics
    orientation: OrientationInfo
    fields: Dict[str, FieldProvenance] = {}
    number_validation: NumberValidation
    qr: QRInfo
    qr_consistency: Optional[QRConsistency] = None
    photo: PhotoInfo
    biometric: BiometricInfo
    forensics: ForensicsInfo
    metadata: MetadataInfo
    offline_ekyc: OfflineEkycInfo

    validation: List[Dict[str, Any]] = []
    contradictions: List[ContradictionItem] = []
    evidence: List[EvidenceItem] = []
    evidence_relations: List[EvidenceRelation] = []

    scores: Scores
    screening: ScreeningInfo
    artifacts: ArtifactsInfo
    audit: AuditInfo
    privacy: PrivacyInfo
    errors: List[Dict[str, Any]] = []
