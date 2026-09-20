from pydantic_settings import BaseSettings
from pathlib import Path
import os

class Settings(BaseSettings):
    app_name: str = "DAKSH Aadhaar Screening"
    module: str = "P3_AADHAAR"
    module_version: str = "1.0.0"
    schema_version: str = "1.0"
    environment: str = "development"
    port: int = 8000
    storage_mode: str = "HASH_ONLY"
    artifacts_dir: str = "./data/artifacts"
    max_file_size_mb: int = 10
    max_pdf_pages: int = 5
    max_zip_size_mb: int = 5
    max_zip_files: int = 20
    mongodb_uri: str = "mongodb://localhost:27017"
    mongodb_db: str = "daksh_aadhaar"
    allow_origins: str = "http://localhost:5173,http://localhost:3000"
    ocr_engine: str = "rapidocr"
    ocr_fallback_enabled: bool = True
    face_threshold: float = 0.6
    audit_chain_file: str = "./data/audit_chain.jsonl"
    blockchain_enabled: bool = False
    blockchain_rpc_url: str = ""
    uidai_qr_cert_path: str = ""
    build_stage: str = "COMPLETE"

    class Config:
        env_file = ".env"
        extra = "ignore"

settings = Settings()

# Resolve paths relative to project root (daksh-aadhaar/)
BASE_DIR = Path(__file__).resolve().parents[3]  # backend/app/config.py -> daksh-aadhaar
# fallback if file in /home/user/daksh-aadhaar/backend/app
try:
    # When running from /home/user/daksh-aadhaar, BASE_DIR should be that
    if (BASE_DIR / "backend").exists():
        PROJECT_ROOT = BASE_DIR
    else:
        # try alternative
        PROJECT_ROOT = Path.cwd()
        if (PROJECT_ROOT / "backend").exists():
            pass
        else:
            PROJECT_ROOT = Path(__file__).resolve().parents[3]
except:
    PROJECT_ROOT = Path.cwd()

def get_artifacts_dir() -> Path:
    p = Path(settings.artifacts_dir)
    if not p.is_absolute():
        p = PROJECT_ROOT / p
    p.mkdir(parents=True, exist_ok=True)
    return p

def get_audit_chain_path() -> Path:
    p = Path(settings.audit_chain_file)
    if not p.is_absolute():
        p = PROJECT_ROOT / p
    p.parent.mkdir(parents=True, exist_ok=True)
    return p
