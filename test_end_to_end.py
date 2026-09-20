import requests, pathlib, json, sys, time
BASE="http://localhost:8000"
samples_dir = pathlib.Path("samples")
tests = [
    ("01_clean.png", "CLEAN EXPECT CLEAR", None),
    ("02_modified_dob.png", "DOB MODIFIED EXPECT REVIEW", None),
    ("07_replaced_photo.png", "PHOTO MODIFIED", None),
    ("10_blurry.png", "BLURRY EXPECT INCONCLUSIVE", None),
    ("11_rotated.png", "ROTATED EXPECT CLEAR after correction", None),
    ("13_qr_contradiction.png", "QR CONTRADICTION EXPECT REVIEW", None),
    ("14_masked.png", "MASKED EXPECT CLEAR with MASKED handling", None),
    ("15_missing_qr.png", "MISSING QR", None),
    ("08_multiple_modifications.png", "MULTIPLE EXPECT HIGH_REVIEW", None),
    ("01_clean.pdf", "PDF CLEAN", None),
]

for fname, desc, extra in tests:
    p = samples_dir / fname
    if not p.exists():
        print(f"SKIP {fname} not found")
        continue
    with open(p,"rb") as f:
        files={"document":(p.name, f.read(), "application/octet-stream")}
        # determine mime
        if fname.endswith(".pdf"):
            files={"document":(p.name, open(p,"rb").read(), "application/pdf")}
        else:
            # need to reopen correctly
            pass
    # Actually reopen properly
    with open(p,"rb") as fh:
        data = fh.read()
        mime = "application/pdf" if p.suffix==".pdf" else "image/png"
        try:
            r = requests.post(f"{BASE}/api/modules/aadhaar", files={"document":(p.name, data, mime)}, data={"persist_artifacts":"true"}, timeout=60)
            j=r.json()
            print(f"\n=== {fname} ({desc}) ===")
            print(f"Status: {j['screening']['status']} | Score: {j['scores']['integrity_score']} | Coverage: {j['scores']['evidence_coverage']}% sufficient:{j['scores']['coverage_sufficient']}")
            print(f"Variant: {j['document_variant']} | DocID: {j['document_identification']['result']}")
            print(f"QR: {j['qr']['status']} decoded:{j['qr']['decoded']} consistency: {j['qr_consistency']['overall']}")
            print(f"Number: {j['number_validation']['format_status']}/{j['number_validation']['checksum_status']}")
            print(f"Photo: {j['photo']['status']} Face: {j['biometric']['status']}")
            print(f"Forensics: {j['forensics']['overall_label']} regions:{len(j['forensics']['regions'])}")
            print(f"Evidence: {len(j['evidence'])} Contradictions: {len(j['contradictions'])}")
            if j['contradictions']:
                for c in j['contradictions']:
                    print(f"  - {c['field']}: {c['source_a']}={c['value_a']} vs {c['source_b']}={c['value_b']} ({c['severity']})")
            print(f"Audit hash: {j['audit']['document_hash'][:16]}... chain:{j['audit']['chain_verified']}")
            # Validate schema version
            assert j["schema_version"]=="1.0"
            assert "case_id" in j
        except Exception as e:
            print(f"FAILED {fname}: {e}")
            import traceback; traceback.print_exc()

# Test face mismatch with ref
print("\n=== FACE MISMATCH TEST ===")
try:
    with open(samples_dir/"01_clean.png","rb") as f:
        doc_data=f.read()
    with open(samples_dir/"ref_face_mismatch.jpg","rb") as f:
        ref_data=f.read()
    r=requests.post(f"{BASE}/api/modules/aadhaar", files={"document":("01_clean.png",doc_data,"image/png"), "reference_face":("ref.jpg",ref_data,"image/jpeg")}, timeout=60)
    j=r.json()
    print(f"Face status with mismatch ref: {j['biometric']['status']} similarity:{j['biometric']['similarity']}")
    print(f"Overall screening: {j['screening']['status']}")
except Exception as e:
    print(f"Face mismatch test failed {e}")

# Test face match
print("\n=== FACE MATCH TEST ===")
try:
    with open(samples_dir/"ref_face_match.jpg","rb") as f:
        ref2=f.read()
    r=requests.post(f"{BASE}/api/modules/aadhaar", files={"document":("01_clean.png",doc_data,"image/png"), "reference_face":("ref2.jpg",ref2,"image/jpeg")}, timeout=60)
    j=r.json()
    print(f"Face status with match ref: {j['biometric']['status']} similarity:{j['biometric']['similarity']}")
except Exception as e:
    print(e)

# Test eKYC
print("\n=== EKYC TEST ===")
# Create dummy eKYC XML
ekyc_xml = b'''<OfflinePaperlessKyc><UidData uid="304332181964"><Poi name="Aarav Kumar" dob="12/04/2005" gender="M"/><Poa house="12/34" street="Gandhi Street" vtc="Salem" dist="Salem" state="Tamil Nadu" pc="636001"/><Pht>dummybase64photo</Pht></UidData></OfflinePaperlessKyc>'''
try:
    r=requests.post(f"{BASE}/api/modules/aadhaar", files={"document":("01_clean.png",doc_data,"image/png"), "offline_ekyc":("ekyc.xml",ekyc_xml,"text/xml")}, timeout=60)
    j=r.json()
    print(f"eKYC status: {j['offline_ekyc']['status']} fields:{j['offline_ekyc']['fields']}")
    print(f"eKYC signature: {j['offline_ekyc']['signature_status']}")
except Exception as e:
    print(e)

# Test corrupted
print("\n=== CORRUPTED TEST ===")
try:
    with open(samples_dir/"19_corrupted.jpg","rb") as f:
        data=f.read()
    r=requests.post(f"{BASE}/api/modules/aadhaar", files={"document":("19_corrupted.jpg",data,"image/jpeg")}, timeout=60)
    j=r.json()
    print(f"Corrupted handling: module_status {j['module_status']} screening {j['screening']['status']} errors:{len(j['errors'])}")
except Exception as e:
    print(e)

print("\nAll end-to-end checks done")
