import cv2
import numpy as np
import re

def estimate_orientation(images, ocr_adapter=None, ocr_results=None):
    """
    Determine orientation (0,90,180,270). MVP: use OCR text orientation cues.
    We test 4 rotations and pick best OCR confidence / keyword match.
    But to avoid heavy compute, we test 0 and 180 first, then 90/270 if needed.
    """
    if not images:
        return {"applied_rotation":0, "detected_rotation":0, "candidate_scores":{"0":1.0}, "confidence":0.5, "method":"HEURISTIC", "ambiguous": False}

    img = images[0]["image"]
    # Simple heuristic: if image w >> h, likely rotated? Not reliable.

    # Try OCR on original and 180
    candidates = {}
    best_rotation = 0
    # if ocr_adapter available, use it to score
    if ocr_adapter and ocr_adapter.is_available() and ocr_results:
        # Use existing ocr_results confidence as baseline for 0
        base_text = " ".join([r.text for r in ocr_results])
        base_conf = np.mean([r.confidence for r in ocr_results if r.confidence>0]) if any(r.confidence>0 for r in ocr_results) else 0
        # keyword score
        keywords = ["aadhaar","government","india","dob","gender","male","female","year"]
        def keyword_score(text):
            txt = text.lower()
            score = sum(1 for k in keywords if k in txt)
            return score
        base_kw = keyword_score(base_text)
        # we consider base as 0 degree score
        candidates["0"] = float(base_conf*10 + base_kw)
        # test 180: rotate image 180 and ocr
        try:
            rot180 = cv2.rotate(img, cv2.ROTATE_180)
            res180 = ocr_adapter.ocr_image(rot180, page=1)
            kw180 = keyword_score(res180.text)
            candidates["180"] = float(res180.confidence*10 + kw180)
            # choose best only if significantly better (margin >1.0) to avoid flipping on noise
            if candidates["180"] > candidates["0"] + 1.0:
                best_rotation = 180
        except:
            candidates["180"] = 0
        # also test 90/270 if both low?
        # only if both scores very low
        if max(candidates.values()) < 2:
            for angle, flag in [("90", cv2.ROTATE_90_CLOCKWISE), ("270", cv2.ROTATE_90_COUNTERCLOCKWISE)]:
                try:
                    rot = cv2.rotate(img, flag)
                    res = ocr_adapter.ocr_image(rot, page=1)
                    kw = keyword_score(res.text)
                    sc = float(res.confidence*10 + kw)
                    candidates[angle] = sc
                    if sc > candidates.get(str(best_rotation),0):
                        best_rotation = int(angle)
                except:
                    candidates[angle]=0
    else:
        # No OCR, use image moment orientation? fallback to 0.
        candidates["0"] = 1.0
        best_rotation = 0

    # Normalize scores to 0-1
    max_s = max(candidates.values()) if candidates else 1
    normalized = {k: round(v/max_s,3) if max_s>0 else 0 for k,v in candidates.items()}
    confidence = normalized.get(str(best_rotation),0.5)
    ambiguous = len([v for v in candidates.values() if v > max_s*0.85]) >1
    # If ambiguous, prefer 0 to avoid false rotation
    if ambiguous and best_rotation != 0:
        # Check if best is only marginally better; keep 0 if ambiguous
        if abs(candidates.get(str(best_rotation),0) - candidates.get("0",0)) < 2.0:
            best_rotation = 0
            confidence = normalized.get("0",0.5)

    return {
        "applied_rotation": best_rotation,
        "detected_rotation": best_rotation,
        "candidate_scores": candidates,
        "confidence": float(confidence),
        "method": "OCR_KEYWORD_HEURISTIC" if ocr_adapter and ocr_adapter.is_available() else "HEURISTIC",
        "ambiguous": ambiguous
    }

def correct_orientation(images, rotation):
    if rotation == 0:
        return images
    corrected=[]
    for item in images:
        img = item["image"]
        if rotation == 90:
            img = cv2.rotate(img, cv2.ROTATE_90_CLOCKWISE)
        elif rotation == 180:
            img = cv2.rotate(img, cv2.ROTATE_180)
        elif rotation == 270:
            img = cv2.rotate(img, cv2.ROTATE_90_COUNTERCLOCKWISE)
        corrected.append({"image": img, "page": item["page"], "width": img.shape[1], "height": img.shape[0]})
    return corrected
