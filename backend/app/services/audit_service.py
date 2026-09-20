import json
import hashlib
from pathlib import Path
from datetime import datetime, timezone
import uuid
from ..utils.hashing import sha256_bytes, canonical_json
from ..config import get_audit_chain_path

def create_audit_event(case_id: str, document_hash: str, manifest_hash: str, module_version="1.0.0", event_type="SCREENING_COMPLETED"):
    audit_path = get_audit_chain_path()
    timestamp = datetime.now(timezone.utc).isoformat()
    event_id = f"EVT-{uuid.uuid4().hex[:8].upper()}"
    # Read previous hash
    previous_hash = "GENESIS"
    if audit_path.exists():
        try:
            with open(audit_path, "r") as f:
                lines = f.readlines()
                if lines:
                    last = json.loads(lines[-1])
                    previous_hash = last.get("event_hash", "GENESIS")
        except:
            previous_hash = "GENESIS"

    event = {
        "event_id": event_id,
        "case_id": case_id,
        "timestamp": timestamp,
        "event_type": event_type,
        "module_version": module_version,
        "document_hash": document_hash,
        "manifest_hash": manifest_hash,
        "previous_hash": previous_hash
    }
    canonical = canonical_json(event)
    event_hash = hashlib.sha256((previous_hash + canonical).encode("utf-8")).hexdigest()
    event["event_hash"] = event_hash

    # Append
    try:
        with open(audit_path, "a") as f:
            f.write(canonical_json(event) + "\n")
    except Exception as e:
        print(f"Audit append failed: {e}")

    return event

def verify_chain():
    audit_path = get_audit_chain_path()
    if not audit_path.exists():
        return {"verified": True, "events":0, "message":"No chain yet"}
    try:
        with open(audit_path, "r") as f:
            lines = [json.loads(l) for l in f if l.strip()]
        prev = "GENESIS"
        for ev in lines:
            expected_prev = ev.get("previous_hash")
            if expected_prev != prev:
                return {"verified": False, "events": len(lines), "message": f"Chain broken at {ev.get('event_id')}"}
            # recompute hash
            copy = {k:v for k,v in ev.items() if k!="event_hash"}
            canonical = canonical_json(copy)
            computed = hashlib.sha256((prev + canonical).encode("utf-8")).hexdigest()
            if computed != ev.get("event_hash"):
                return {"verified": False, "events": len(lines), "message": f"Hash mismatch at {ev.get('event_id')}"}
            prev = ev.get("event_hash")
        return {"verified": True, "events": len(lines), "message":"Chain verified"}
    except Exception as e:
        return {"verified": False, "events":0, "message": str(e)}

def get_chain_tail(n=5):
    audit_path = get_audit_chain_path()
    if not audit_path.exists():
        return []
    try:
        with open(audit_path, "r") as f:
            lines = [json.loads(l) for l in f if l.strip()]
        return lines[-n:]
    except:
        return []
