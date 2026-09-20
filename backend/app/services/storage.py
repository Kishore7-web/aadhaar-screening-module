import json
from pathlib import Path
from datetime import datetime
from ..config import get_artifacts_dir
import hashlib

class LocalRepository:
    def __init__(self):
        self.base = get_artifacts_dir() / "cases"
        self.base.mkdir(parents=True, exist_ok=True)

    def save(self, case_id: str, data: dict):
        # Save minimal non-sensitive data; but store full standardized JSON for retrieval
        path = self.base / f"{case_id}.json"
        # Ensure no raw PII leakage? We store as provided but masked? Already masked.
        with open(path, "w") as f:
            json.dump(data, f, indent=2)
        return str(path)

    def get(self, case_id: str):
        path = self.base / f"{case_id}.json"
        if not path.exists():
            return None
        with open(path, "r") as f:
            return json.load(f)

    def list_cases(self, limit=50):
        files = sorted(self.base.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
        result=[]
        for p in files[:limit]:
            with open(p, "r") as f:
                data = json.load(f)
                # Return summary
                result.append({
                    "case_id": data.get("case_id"),
                    "generated_at": data.get("generated_at"),
                    "screening_status": data.get("screening",{}).get("status"),
                    "integrity_score": data.get("scores",{}).get("integrity_score"),
                    "evidence_coverage": data.get("scores",{}).get("evidence_coverage"),
                    "document_variant": data.get("document_variant")
                })
        return result

    def exists(self, case_id: str):
        return (self.base / f"{case_id}.json").exists()

# Mongo adapter placeholder
class MongoRepository:
    def __init__(self, uri, db_name):
        self.uri = uri
        self.db_name = db_name
        self.available = False
        self.client = None
        try:
            from pymongo import MongoClient
            client = MongoClient(uri, serverSelectionTimeoutMS=2000)
            client.admin.command('ping')
            self.client = client
            self.db = client[db_name]
            self.available = True
        except Exception as e:
            print(f"Mongo not available: {e}")
            self.available = False

    def save(self, case_id: str, data: dict):
        if not self.available:
            return None
        try:
            self.db.cases.update_one({"case_id": case_id}, {"$set": data}, upsert=True)
            return f"mongo:{case_id}"
        except Exception as e:
            print(f"Mongo save failed: {e}")
            return None

    def get(self, case_id: str):
        if not self.available:
            return None
        try:
            return self.db.cases.find_one({"case_id": case_id}, {"_id":0})
        except:
            return None

    def list_cases(self, limit=50):
        if not self.available:
            return []
        try:
            cur = self.db.cases.find({}, {"case_id":1, "generated_at":1, "screening":1, "scores":1, "_id":0}).sort("generated_at", -1).limit(limit)
            result=[]
            for doc in cur:
                result.append({
                    "case_id": doc.get("case_id"),
                    "generated_at": doc.get("generated_at"),
                    "screening_status": doc.get("screening",{}).get("status"),
                    "integrity_score": doc.get("scores",{}).get("integrity_score"),
                    "evidence_coverage": doc.get("scores",{}).get("evidence_coverage")
                })
            return result
        except:
            return []

class Repository:
    def __init__(self):
        self.local = LocalRepository()
        self.mongo = None
        # Attempt mongo init but don't fail
        try:
            from ..config import settings
            if settings.mongodb_uri:
                self.mongo = MongoRepository(settings.mongodb_uri, settings.mongodb_db)
                # if mongo not available, fallback to local only
                if not self.mongo.available:
                    self.mongo = None
        except:
            self.mongo = None

    def save(self, case_id, data):
        # Try mongo first, then local always
        if self.mongo and self.mongo.available:
            try:
                self.mongo.save(case_id, data)
            except:
                pass
        return self.local.save(case_id, data)

    def get(self, case_id):
        if self.mongo and self.mongo.available:
            r = self.mongo.get(case_id)
            if r:
                return r
        return self.local.get(case_id)

    def list_cases(self, limit=50):
        if self.mongo and self.mongo.available:
            lst = self.mongo.list_cases(limit)
            if lst:
                return lst
        return self.local.list_cases(limit)

repo = Repository()
