#!/usr/bin/env python3
"""
Synthetic Aadhaar-like test document generator for DAKSH P3
Generates controlled synthetic documents with watermark "SYNTHETIC TEST DOCUMENT"
"""
import os, sys, json, random, textwrap
from pathlib import Path
import hashlib
import base64
import qrcode
from PIL import Image, ImageDraw, ImageFont
import io
import cv2
import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SAMPLES_DIR = PROJECT_ROOT / "samples"
SAMPLES_DIR.mkdir(parents=True, exist_ok=True)

# Verhoeff utilities (copy)
_d = [
    [0,1,2,3,4,5,6,7,8,9],
    [1,2,3,4,0,6,7,8,9,5],
    [2,3,4,0,1,7,8,9,5,6],
    [3,4,0,1,2,8,9,5,6,7],
    [4,0,1,2,3,9,5,6,7,8],
    [5,9,8,7,6,0,4,3,2,1],
    [6,5,9,8,7,1,0,4,3,2],
    [7,6,5,9,8,2,1,0,4,3],
    [8,7,6,5,9,3,2,1,0,4],
    [9,8,7,6,5,4,3,2,1,0]
]
_p = [
    [0,1,2,3,4,5,6,7,8,9],
    [1,5,7,6,2,8,3,0,9,4],
    [5,8,0,3,7,9,6,1,4,2],
    [8,9,1,6,0,4,3,7,2,5],
    [9,4,5,3,1,2,6,8,7,0],
    [4,2,8,6,5,7,3,9,0,1],
    [2,7,9,3,8,0,6,4,1,5],
    [7,0,4,6,9,1,3,2,5,8]
]
_inv = [0,4,3,2,1,5,6,7,8,9]
def verhoeff_generate(num_str):
    c=0
    for i,ch in enumerate(reversed(num_str)):
        c=_d[c][_p[(i+1)%8][int(ch)]]
    return str(_inv[c])

def generate_valid_aadhaar():
    # generate 11 random digits not starting with 0/1
    first = str(random.randint(2,9))
    rest = "".join(str(random.randint(0,9)) for _ in range(10))
    base = first+rest
    check = verhoeff_generate(base)
    return base+check

def mask_aadhaar(num):
    return f"XXXX XXXX {num[-4:]}"

# Use deterministic seed for reproducibility per sample type? But allow random per run but deterministic via sample id? We'll use fixed seed for each sample.

def get_font(size=24):
    # Try to load a truetype, fallback to default
    try:
        # PIL default has DejaVu? Try common paths
        for p in ["/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf"]:
            if Path(p).exists():
                return ImageFont.truetype(p, size)
        return ImageFont.load_default()
    except:
        return ImageFont.load_default()

def create_qr_data(name, dob, gender, uid, address_composed=None):
    # Create XML-like string mimicking UIDAI PrintLetterBarcodeData
    # Using attributes
    # dob format dd/mm/yyyy or yob
    # Extract yob from dob
    yob = dob.split("/")[-1] if "/" in dob else dob[:4]
    dist = "Salem"
    state = "Tamil Nadu"
    pc = "636001"
    co = "S/O R Kumar"
    house = "12/34"
    street = "Gandhi Street"
    vtc = "Salem"
    # Build xml
    xml = f'<PrintLetterBarcodeData uid="{uid}" name="{name}" gender="{gender[0]}" yob="{yob}" co="{co}" house="{house}" street="{street}" vtc="{vtc}" dist="{dist}" state="{state}" pc="{pc}" dob="{dob}"/>'
    return xml

def generate_aadhaar_image(name, dob, gender, aadhaar_number, address, qr_data_str, photo_color=(180,180,220), tamper=None, variant="physical", blur=False, rotate=0, recompress=False, masked=False):
    # Create 1000x650 image
    W, H = 1000, 650
    img = Image.new("RGB", (W,H), color=(255,255,255))
    draw = ImageDraw.Draw(img)
    # Border
    draw.rectangle([0,0,W-1,H-1], outline=(0,0,0), width=2)
    # Header
    try:
        font_title = get_font(22)
        font_small = get_font(16)
        font_medium = get_font(18)
        font_large = get_font(20)
        font_watermark = get_font(28)
    except:
        font_title = ImageFont.load_default()
        font_small = ImageFont.load_default()
        font_medium = ImageFont.load_default()
        font_large = ImageFont.load_default()
        font_watermark = ImageFont.load_default()

    # Top bar
    draw.rectangle([0,0,W,70], fill=(0,51,102))
    draw.text((W//2, 20), "Government of India", fill=(255,255,255), font=font_medium, anchor="mm")
    draw.text((W//2, 45), "Unique Identification Authority of India", fill=(255,255,0), font=font_small, anchor="mm")
    # Watermark
    # Diagonal watermark text
    watermark = "SYNTHETIC TEST DOCUMENT"
    # Create transparent overlay for watermark?
    # Draw semi-transparent watermark
    # Since PIL not easily translucent, draw light gray
    # We will draw watermark at bottom center in red
    draw.text((W//2, H-30), "SYNTHETIC TEST DOCUMENT  •  NOT A REAL AADHAAR", fill=(255,0,0), font=font_small, anchor="mm")
    # Also diagonal large faint
    # Create a faint text by drawing with low contrast? Use light gray
    # We'll draw at center rotated? For simplicity draw faint at center
    # Not needed

    # Photo region (left)
    photo_x, photo_y, photo_w, photo_h = 40, 90, 180, 220
    draw.rectangle([photo_x, photo_y, photo_x+photo_w, photo_y+photo_h], fill=photo_color, outline=(0,0,0))
    # Draw face-like shape inside photo (circle for head, simple)
    # Head
    cx, cy = photo_x + photo_w//2, photo_y + photo_h//3
    draw.ellipse([cx-40, cy-35, cx+40, cy+35], fill=(230,190,160), outline=(0,0,0))
    # Eyes
    draw.ellipse([cx-20, cy-10, cx-10, cy+0], fill=(0,0,0))
    draw.ellipse([cx+10, cy-10, cx+20, cy+0], fill=(0,0,0))
    # Smile
    draw.arc([cx-15, cy+5, cx+15, cy+20], start=0, end=180, fill=(0,0,0), width=2)
    # If replaced photo tamper: change color significantly
    if tamper == "photo_replaced":
        draw.rectangle([photo_x, photo_y, photo_x+photo_w, photo_y+photo_h], fill=(100,180,100), outline=(255,0,0), width=3)
        # Different face
        draw.ellipse([cx-40, cy-35, cx+40, cy+35], fill=(180,120,80), outline=(0,0,0))
        draw.rectangle([cx-20, cy-10, cx-10, cy+0], fill=(0,0,0))
        draw.rectangle([cx+10, cy-10, cx+20, cy+0], fill=(0,0,0))

    # Text fields (middle)
    text_x = 250
    text_y = 100
    line_gap = 36

    # Apply tamper to fields: if tampered_dob, use different dob for printed vs QR
    printed_name = name
    printed_dob = dob
    printed_gender = gender
    printed_aadhaar = aadhaar_number if not masked else mask_aadhaar(aadhaar_number)
    printed_address = address

    if tamper == "dob":
        # Change printed DOB by 1 year
        # dob is like 12/04/2005 => change to 12/04/2004
        parts = dob.split("/")
        if len(parts)==3:
            printed_dob = f"{parts[0]}/{parts[1]}/{int(parts[2])-1}"
        else:
            printed_dob = "01/01/2000"
    elif tamper == "name":
        printed_name = "Vikram Singh" if name!="Vikram Singh" else "Amit Kumar"
    elif tamper == "number":
        # change last digit
        last = aadhaar_number[-1]
        new_last = str((int(last)+1)%10)
        printed_aadhaar = aadhaar_number[:-1]+new_last
        printed_aadhaar = f"{printed_aadhaar[:4]} {printed_aadhaar[4:8]} {printed_aadhaar[8:]}"
    elif tamper == "gender":
        printed_gender = "Female" if gender=="Male" else "Male"
    elif tamper == "address":
        printed_address = "XX Street, Chennai, Tamil Nadu - 600001"
    elif tamper == "multiple":
        # Change dob and name
        parts = dob.split("/")
        if len(parts)==3:
            printed_dob = f"{parts[0]}/{parts[1]}/{int(parts[2])-2}"
        printed_name = "Rahul Verma"
        # Also will create forensic-like artifact: draw red rectangle near DOB? We'll add after
    elif tamper == "photo_replaced":
        # name unchanged but photo replaced, for forensics
        pass

    # Draw printed fields
    draw.text((text_x, text_y), f"Name: {printed_name}", fill=(0,0,0), font=font_medium)
    draw.text((text_x, text_y+line_gap), f"DOB: {printed_dob}", fill=(0,0,0), font=font_medium)
    draw.text((text_x, text_y+2*line_gap), f"Gender: {printed_gender}", fill=(0,0,0), font=font_medium)
    draw.text((text_x, text_y+3*line_gap), f"Aadhaar: {printed_aadhaar}", fill=(0,0,0), font=font_medium)
    # Extra formatting for masked
    if masked:
        draw.text((text_x, text_y+4*line_gap), f"Address: {printed_address[:45]}", fill=(0,0,0), font=font_small)
        draw.text((text_x, text_y+4*line_gap+20), f"{printed_address[45:90]}", fill=(0,0,0), font=font_small)
    else:
        draw.text((text_x, text_y+4*line_gap), f"Address: {printed_address[:45]}", fill=(0,0,0), font=font_small)
        draw.text((text_x, text_y+4*line_gap+20), f"{printed_address[45:90]}", fill=(0,0,0), font=font_small)

    # Draw redaction or highlight for tampered DOB? Forensic signal: add subtle noise-like rectangle near DOB for tamper cases
    if tamper in ["dob","multiple"]:
        # Simulate tampering by drawing slightly off-color rectangle behind DOB text
        # This may be detected by forensics as sharpness inconsistency
        # But we will also add a small cloned patch?
        # Draw a white rectangle slightly misaligned
        tx, ty = text_x, text_y+line_gap
        # cover DOB line with white then rewrite with slightly different bg?
        draw.rectangle([tx-2, ty-2, tx+220, ty+22], fill=(250,250,250), outline=(200,200,200))
        draw.text((tx, ty), f"DOB: {printed_dob}", fill=(0,0,80), font=font_medium)

    # QR code (right side)
    qr_size = 180
    qr_x, qr_y = W - qr_size - 40, 100
    # Generate QR image
    qr = qrcode.QRCode(version=4, error_correction=qrcode.constants.ERROR_CORRECT_M, box_size=4, border=1)
    qr.add_data(qr_data_str)
    qr.make(fit=True)
    qr_img = qr.make_image(fill_color="black", back_color="white").convert("RGB")
    qr_img = qr_img.resize((qr_size, qr_size), Image.NEAREST)
    # If tamper == qr_contradiction, generate QR with original (non-tampered) data while printed is tampered
    # Already qr_data_str is original? For dob tamper, qr_data should be original dob, printed is tampered.
    # For consistency, when tamper is dob, qr_data should be original; we already set qr_data_str before tamper. So good.
    # But for pure qr_contradiction case, we will handle via caller
    img.paste(qr_img, (qr_x, qr_y))
    draw.rectangle([qr_x, qr_y, qr_x+qr_size, qr_y+qr_size], outline=(0,0,0))
    draw.text((qr_x+qr_size//2, qr_y+qr_size+15), "QR Code", fill=(0,0,0), font=font_small, anchor="mm")

    # Footer
    draw.text((W//2, 600), "This is a synthetic test document for DAKSH screening. Not valid for official use.", fill=(100,100,100), font=font_small, anchor="mm")
    draw.text((W//2, 620), "SYNTHETIC TEST DOCUMENT  —  NOT A REAL AADHAAR", fill=(255,0,0), font=font_small, anchor="mm")

    # Variant adjustments: if missing QR, cover it
    if tamper == "missing_qr":
        draw.rectangle([qr_x-10, qr_y-10, qr_x+qr_size+10, qr_y+qr_size+30], fill=(255,255,255), outline=(255,255,255))
        draw.text((qr_x+qr_size//2, qr_y+qr_size//2), "QR\nMISSING", fill=(150,150,150), font=font_medium, anchor="mm", align="center")
    if tamper == "missing_photo":
        draw.rectangle([photo_x-5, photo_y-5, photo_x+photo_w+5, photo_y+photo_h+5], fill=(255,255,255), outline=(255,255,255))
        draw.text((photo_x+photo_w//2, photo_y+photo_h//2), "PHOTO\nMISSING", fill=(150,150,150), font=font_medium, anchor="mm", align="center")

    # Handle rotation
    if rotate !=0:
        # rotate whole image
        img = img.rotate(rotate, expand=True, fillcolor=(255,255,255))

    # Convert to bytes via OpenCV for blur/recompress
    # PIL to numpy
    cv_img = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)

    # Blur
    if blur:
        cv_img = cv2.GaussianBlur(cv_img, (15,15), 0)

    # Recompress (simulate screenshot recompression): encode JPEG low quality then decode
    if recompress:
        encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), 40]
        _, enc = cv2.imencode('.jpg', cv_img, encode_param)
        cv_img = cv2.imdecode(enc, cv2.IMREAD_COLOR)
        # encode again at higher quality to simulate double compression artifacts
        _, enc2 = cv2.imencode('.jpg', cv_img, [int(cv2.IMWRITE_JPEG_QUALITY), 85])
        cv_img = cv2.imdecode(enc2, cv2.IMREAD_COLOR)

    # Partial document (crop)
    if tamper == "partial":
        h,w = cv_img.shape[:2]
        # crop to half
        cv_img = cv_img[0:h//2, 0:w]

    # Save
    return cv_img

def generate_all():
    random.seed(42)
    # Clean base data
    base_name = "Aarav Kumar"
    base_dob = "12/04/2005"
    base_gender = "Male"
    base_aadhaar = generate_valid_aadhaar()
    base_address = "12/34 Gandhi Street, Salem, Tamil Nadu - 636001"
    print(f"Base Aadhaar (valid): {base_aadhaar} masked: {mask_aadhaar(base_aadhaar)}")
    # Store base for later reference? Save metadata
    base_qr = create_qr_data(base_name, base_dob, base_gender, base_aadhaar, base_address)
    # Ensure base_qr uses valid data
    # Create samples list
    samples = [
        {"id":"01_clean", "tamper":None, "variant":"clean", "expected":"CLEAR", "desc":"Clean synthetic document", "blur":False,"rotate":0,"masked":False},
        {"id":"02_modified_dob", "tamper":"dob", "variant":"dob_tamper", "expected":"REVIEW", "desc":"DOB modified, QR contradiction"},
        {"id":"03_modified_name", "tamper":"name", "variant":"name_tamper", "expected":"REVIEW"},
        {"id":"04_modified_number", "tamper":"number", "variant":"number_tamper", "expected":"REVIEW"},
        {"id":"05_modified_gender", "tamper":"gender", "variant":"gender_tamper", "expected":"REVIEW"},
        {"id":"06_modified_address", "tamper":"address", "variant":"address_tamper", "expected":"LOW_CONCERN"},
        {"id":"07_replaced_photo", "tamper":"photo_replaced", "variant":"photo_tamper", "expected":"REVIEW"},
        {"id":"08_multiple_modifications", "tamper":"multiple", "variant":"multiple", "expected":"HIGH_REVIEW"},
        {"id":"09_face_mismatch", "tamper":None, "variant":"face_mismatch", "expected":"REVIEW", "note":"Will be tested with different reference face"},
        {"id":"10_blurry", "tamper":None, "variant":"blurry", "expected":"INCONCLUSIVE", "blur":True},
        {"id":"11_rotated", "tamper":None, "variant":"rotated", "expected":"CLEAR or REVIEW after correction", "rotate":90},
        {"id":"12_screenshot_recompressed", "tamper":None, "variant":"recompressed", "expected":"LOW_CONCERN or REVIEW", "recompress":True},
        {"id":"13_qr_contradiction", "tamper":"dob", "variant":"qr_contradiction", "expected":"REVIEW", "desc":"QR vs printed contradiction"},
        {"id":"14_masked", "tamper":None, "variant":"masked", "expected":"CLEAR (masked handling)", "masked":True},
        {"id":"15_missing_qr", "tamper":"missing_qr", "variant":"missing_qr", "expected":"LOW_CONCERN or CLEAR (QR not required)"},
        {"id":"16_missing_photo", "tamper":"missing_photo", "variant":"missing_photo", "expected":"REVIEW"},
        {"id":"17_low_ocr", "tamper":None, "variant":"low_ocr", "expected":"INCONCLUSIVE", "blur":True, "recompress":True},
        {"id":"18_partial_document", "tamper":"partial", "variant":"partial", "expected":"INCONCLUSIVE"},
        {"id":"19_module_failure", "tamper":None, "variant":"partial", "expected":"PARTIAL handling", "note":"Will test corrupted file"},
        {"id":"20_multi_source_contradiction", "tamper":"multiple", "variant":"three_source", "expected":"HIGH_REVIEW"},
    ]

    metadata_all = {}
    for s in samples:
        sid = s["id"]
        tamper = s.get("tamper")
        blur = s.get("blur", False)
        rotate = s.get("rotate", 0)
        recompress = s.get("recompress", False)
        masked = s.get("masked", False)
        # For QR contradiction special? Already handled via tamper dob
        # For face_mismatch, just generate clean but will test with different ref face later
        # For 20 etc, just use multiple
        # Generate QR data: for tamper cases where printed mismatched, QR should contain original correct data to create contradiction
        qr_name = base_name
        qr_dob = base_dob
        qr_gender = base_gender
        qr_uid = base_aadhaar
        # If tamper is number, QR should have original valid number? But printed has invalid? We'll keep QR original
        # That will create mismatch for number as well but checksum invalid will be independent.
        # For photo_replaced, QR unchanged
        # So QR always original base
        qr_data = create_qr_data(qr_name, qr_dob, qr_gender, qr_uid, base_address)
        # Special handling for masked: QR still has full uid but printed is masked
        # That's okay, consistency should handle masked vs full

        # If missing_qr or missing_photo tamper, we still generate QR data but will visually hide

        cv_img = generate_aadhaar_image(
            name=base_name,
            dob=base_dob,
            gender=base_gender,
            aadhaar_number=base_aadhaar,
            address=base_address,
            qr_data_str=qr_data,
            tamper=tamper,
            variant=s["variant"],
            blur=blur,
            rotate=rotate,
            recompress=recompress,
            masked=masked
        )

        # Save as PNG and JPG versions? Save PNG for high quality
        png_path = SAMPLES_DIR / f"{sid}.png"
        jpg_path = SAMPLES_DIR / f"{sid}.jpg"
        cv2.imwrite(str(png_path), cv_img)
        # also JPG
        cv2.imwrite(str(jpg_path), cv_img, [int(cv2.IMWRITE_JPEG_QUALITY), 95])

        # For 19_module_failure: create a corrupted PDF? We'll create after loop

        # Create metadata json
        meta = {
            "sample_id": f"AAD-{sid.upper()}",
            "file": f"{sid}.png",
            "attack": s.get("tamper") or "none",
            "variant": s.get("variant"),
            "expected_evidence": [],
            "expected_status": s.get("expected"),
            "description": s.get("desc", s.get("variant")),
            "base_aadhaar": base_aadhaar,
            "masked_aadhaar": mask_aadhaar(base_aadhaar),
            "qr_data": qr_data,
            "fields": {
                "name": base_name,
                "dob": base_dob,
                "gender": base_gender,
                "aadhaar": base_aadhaar,
                "masked": mask_aadhaar(base_aadhaar) if masked else base_aadhaar,
                "address": base_address
            },
            "printed_fields": {
                "name": base_name if tamper not in ["name","multiple"] else ("Vikram Singh" if tamper=="name" else "Rahul Verma"),
                "dob": base_dob if tamper not in ["dob","multiple"] else ("11/04/2004" if tamper=="dob" else "12/04/2003"),
                "gender": base_gender if tamper!="gender" else ("Female" if base_gender=="Male" else "Male"),
                "aadhaar": base_aadhaar if tamper!="number" else base_aadhaar[:-1]+str((int(base_aadhaar[-1])+1)%10)
            },
            "blur": blur,
            "rotate": rotate,
            "recompress": recompress,
            "masked_variant": masked
        }
        # Expected evidence hints
        if tamper=="dob":
            meta["expected_evidence"] = ["QR_PRINTED_CONTRADICTION", "FORENSIC_LOCAL_ANOMALY"]
        elif tamper=="name":
            meta["expected_evidence"] = ["QR_PRINTED_CONTRADICTION"]
        elif tamper=="number":
            meta["expected_evidence"] = ["CHECKSUM_INVALID"]
        elif tamper=="photo_replaced":
            meta["expected_evidence"] = ["FORENSIC_PHOTO_ANOMALY"]
        elif tamper=="multiple":
            meta["expected_evidence"] = ["QR_PRINTED_CONTRADICTION", "FORENSIC_LOCAL_ANOMALY", "MULTIPLE_MISMATCH"]
        elif blur or s["id"] in ["10_blurry","17_low_ocr"]:
            meta["expected_evidence"] = ["LOW_QUALITY", "LOW_COVERAGE"]
        elif masked:
            meta["expected_evidence"] = ["MASKED_AADHAAR"]
        elif tamper=="missing_qr":
            meta["expected_evidence"] = ["QR_NOT_PRESENT"]
        elif tamper=="missing_photo":
            meta["expected_evidence"] = ["PHOTO_NOT_FOUND"]

        metadata_all[sid] = meta
        # Save individual meta
        with open(SAMPLES_DIR / f"{sid}.json", "w") as f:
            json.dump(meta, f, indent=2)
        print(f"Generated {sid}.png ({cv_img.shape[1]}x{cv_img.shape[0]}) tamper={tamper} rotate={rotate} blur={blur}")

    # Additional: generate PDF version of clean
    try:
        clean_png = SAMPLES_DIR / "01_clean.png"
        if clean_png.exists():
            img = Image.open(clean_png)
            pdf_path = SAMPLES_DIR / "01_clean.pdf"
            img.save(pdf_path, "PDF", resolution=200)
            print(f"Generated PDF {pdf_path}")
            # Also rotated PDF? copy
            rotated_png = SAMPLES_DIR / "11_rotated.png"
            if rotated_png.exists():
                img2 = Image.open(rotated_png)
                pdf2 = SAMPLES_DIR / "11_rotated.pdf"
                img2.save(pdf2, "PDF")
                print(f"Generated PDF {pdf2}")
    except Exception as e:
        print(f"PDF generation failed: {e}")

    # Create corrupted file for 19
    corrupted_path = SAMPLES_DIR / "19_corrupted.jpg"
    with open(corrupted_path, "wb") as f:
        f.write(b"This is not an image, corrupted content \x00\x01\x02")
    print("Created corrupted sample 19_corrupted.jpg")

    # Create reference face images for 09_face_mismatch testing
    # Generate two distinct face images (synthetic)
    # Simple: create face with different colors
    def create_face(color1, color2, filename):
        img = np.ones((300,300,3), dtype=np.uint8)*255
        # face ellipse
        cv2.ellipse(img, (150,150), (80,100), 0,0,360, color1, -1)
        cv2.circle(img, (120,130), 15, (0,0,0), -1)
        cv2.circle(img, (180,130), 15, (0,0,0), -1)
        cv2.ellipse(img, (150,180), (30,20), 0,0,180, (0,0,0), 2)
        cv2.imwrite(str(SAMPLES_DIR / filename), img)
    create_face((200,150,120), (0,0,0), "ref_face_match.jpg")
    create_face((100,180,100), (0,0,0), "ref_face_mismatch.jpg")
    print("Generated reference faces")

    # Save overall manifest
    with open(SAMPLES_DIR / "manifest.json", "w") as f:
        json.dump(metadata_all, f, indent=2)
    print(f"Done. Generated {len(metadata_all)} samples in {SAMPLES_DIR}")

if __name__ == "__main__":
    generate_all()
