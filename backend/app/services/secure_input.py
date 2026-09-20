import os
import re
import zipfile
from pathlib import Path
from fastapi import UploadFile
import tempfile

ALLOWED_EXTS = {".jpg",".jpeg",".png",".pdf"}
ALLOWED_MIME = {"image/jpeg","image/png","application/pdf","image/jpg"}
ALLOWED_EKYC_EXTS = {".xml",".zip"}

MAX_FILE_SIZE = 10*1024*1024
MAX_ZIP_SIZE = 5*1024*1024
MAX_PDF_PAGES = 10

def sanitize_filename(fname: str) -> str:
    if not fname:
        return "document"
    base = os.path.basename(fname)
    base = re.sub(r"[^a-zA-Z0-9._-]", "_", base)
    base = base.strip("._")
    if not base:
        base = "document"
    # limit length
    if len(base) > 100:
        name, ext = os.path.splitext(base)
        base = name[:90] + ext
    return base

def check_path_traversal(fname: str) -> bool:
    return ".." in fname or "/" in fname or "\\" in fname

def validate_upload(file: UploadFile, max_size: int = MAX_FILE_SIZE):
    errors = []
    fname = file.filename or "document"
    sanitized = sanitize_filename(fname)
    ext = Path(sanitized).suffix.lower()
    # extension check
    if ext not in ALLOWED_EXTS:
        errors.append(f"Unsupported extension {ext}. Allowed: {ALLOWED_EXTS}")

    # we will check size after reading
    return sanitized, ext, errors

def magic_check(data: bytes, ext: str):
    # simple magic byte validation
    if ext in [".jpg",".jpeg"]:
        if not data.startswith(b"\xff\xd8\xff"):
            return "FAIL: JPEG magic mismatch"
    elif ext == ".png":
        if not data.startswith(b"\x89PNG"):
            return "FAIL: PNG magic mismatch"
    elif ext == ".pdf":
        if not data.startswith(b"%PDF"):
            return "FAIL: PDF magic mismatch"
    return "PASS"

def save_temp_file(data: bytes, suffix: str):
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
    tmp.write(data)
    tmp.close()
    return Path(tmp.name)

def validate_and_save_document(file: UploadFile, data: bytes):
    fname = file.filename or "document"
    sanitized = sanitize_filename(fname)
    ext = Path(sanitized).suffix.lower()
    errors = []
    security_notes = []
    
    if ext not in ALLOWED_EXTS:
        errors.append({"code":"UNSUPPORTED_EXTENSION","message":f"Extension {ext} not allowed"})
        return None, errors, security_notes, sanitized, ext
    
    if len(data) > MAX_FILE_SIZE:
        errors.append({"code":"FILE_TOO_LARGE","message":f"File size {len(data)} exceeds limit {MAX_FILE_SIZE}"})
        return None, errors, security_notes, sanitized, ext
    
    if len(data) == 0:
        errors.append({"code":"EMPTY_FILE","message":"File is empty"})
        return None, errors, security_notes, sanitized, ext

    magic_result = magic_check(data, ext)
    security_notes.append(f"Magic check: {magic_result}")
    if "FAIL" in magic_result:
        errors.append({"code":"MIME_MISMATCH","message":magic_result})
        return None, errors, security_notes, sanitized, ext
    
    # check traversal
    if check_path_traversal(file.filename or ""):
        security_notes.append("Path traversal pattern detected in original filename")
    
    # Save temp
    tmp_path = save_temp_file(data, ext)
    return tmp_path, errors, security_notes, sanitized, ext

def validate_ekyc_upload(file: UploadFile, data: bytes):
    errors=[]
    if file is None or data is None:
        return None, errors
    fname = sanitize_filename(file.filename or "ekyc.zip")
    ext = Path(fname).suffix.lower()
    if ext not in ALLOWED_EKYC_EXTS:
        errors.append({"code":"EKYC_UNSUPPORTED","message":f"eKYC extension {ext} not allowed, use .xml or .zip"})
        return None, errors
    if len(data) > MAX_ZIP_SIZE:
        errors.append({"code":"EKYC_TOO_LARGE","message":"eKYC file too large"})
        return None, errors
    # zip traversal check
    if ext == ".zip":
        try:
            import io
            z = zipfile.ZipFile(io.BytesIO(data))
            for info in z.infolist():
                if ".." in info.filename or info.filename.startswith("/") or "\\" in info.filename:
                    errors.append({"code":"ZIP_TRAVERSAL","message":f"Unsafe zip entry {info.filename}"})
                    return None, errors
                if info.file_size > MAX_ZIP_SIZE:
                    errors.append({"code":"ZIP_ENTRY_TOO_LARGE","message":f"Entry {info.filename} too large"})
                    return None, errors
            if len(z.infolist()) > 20:
                errors.append({"code":"ZIP_TOO_MANY_FILES","message":"Too many files in zip"})
                return None, errors
        except zipfile.BadZipFile:
            errors.append({"code":"BAD_ZIP","message":"Invalid zip file"})
            return None, errors
    tmp_path = save_temp_file(data, ext)
    return tmp_path, errors

def cleanup_temp(path: Path):
    try:
        if path and path.exists():
            path.unlink()
    except:
        pass
