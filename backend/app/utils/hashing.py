import hashlib
import json
from pathlib import Path

def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()

def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()

def sha256_str(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()

def canonical_json(obj) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)

def mask_aadhaar(num: str) -> str:
    if not num:
        return ""
    digits = "".join(c for c in num if c.isdigit())
    if len(digits) < 4:
        return "XXXX XXXX XXXX"
    if len(digits) == 12:
        return f"XXXX XXXX {digits[-4:]}"
    # masked like XXXX XXXX 9012 or 8 digits
    return f"XXXX XXXX {digits[-4:]}"

def mask_generic(value: str, visible=4) -> str:
    if not value or len(value) <= visible:
        return "****"
    return "*" * (len(value)-visible) + value[-visible:]
