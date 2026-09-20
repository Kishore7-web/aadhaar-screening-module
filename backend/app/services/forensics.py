import cv2
import numpy as np
import time

def analyze_forensics(image, fields=None):
    """
    Practical forensic checks:
    - noise inconsistency (local variance)
    - sharpness inconsistency (Laplacian variance per block)
    - ELA-like (recompression) - JPEG quality double compression detection via DCT?
    - edge discontinuity
    Returns regions
    """
    start = time.time()
    regions = []
    signals = []
    notes = []

    if image is None:
        return {"analyzed": False, "signals": [], "regions": [], "ela_score": None, "noise_score": None, "sharpness_variance": None, "recompression_detected": False, "overall_label": "NOT_CHECKED", "notes": "No image"}

    try:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        h,w = gray.shape

        # 1. Noise inconsistency: compute local variance in 32x32 blocks
        block_size = 32
        noise_map = []
        sharp_map = []
        block_means = []
        for y in range(0, h-block_size, block_size):
            for x in range(0, w-block_size, block_size):
                block = gray[y:y+block_size, x:x+block_size]
                var = float(np.var(block))
                lap = cv2.Laplacian(block, cv2.CV_64F).var()
                noise_map.append(((x,y,w,h), var))
                sharp_map.append(((x,y), lap))
                block_means.append(var)

        if block_means:
            mean_var = np.mean(block_means)
            std_var = np.std(block_means)
            # Identify outlier blocks with variance > mean+2.5*std or < mean-2.5*std (less sensitive)
            threshold_high = mean_var + 2.5*std_var
            threshold_low = max(0, mean_var - 2.5*std_var)
            outliers = [ (x,y) for ((x,y,_,_), var) in noise_map if var>threshold_high or var<threshold_low]
            if outliers:
                # Cluster outliers - if many clustered in region, suspicious
                # Simple: count outlier ratio
                outlier_ratio = len(outliers)/len(noise_map)
                if outlier_ratio > 0.08 and outlier_ratio < 0.35:
                    signals.append(f"Local noise inconsistency detected ({len(outliers)} outlier blocks, ratio {outlier_ratio:.2f})")
                    # Create region bounding boxes around clustered outliers
                    # Find largest connected outlier area approximated by convex hull or bounding rect
                    # Simplify: take min/max of outlier coords
                    xs = [x for x,y in outliers]
                    ys = [y for x,y in outliers]
                    rx, ry = min(xs), min(ys)
                    rw, rh = max(xs)-rx+block_size, max(ys)-ry+block_size
                    # Avoid huge region covering whole image and avoid QR area (right side)
                    # QR typically at top-right, high variance expected
                    is_qr_area = (rx > w*0.65 and ry < h*0.4)
                    if not is_qr_area and rw*w < 0.8*w*h and rw>40 and rh>40 and rw*h < 0.5*w*h:
                        regions.append({
                            "region_id": "FOR-001",
                            "reason": "Localized noise variance anomaly - possible localized editing or recompression",
                            "severity": "MEDIUM",
                            "confidence": round(float(min(0.85, outlier_ratio*2.5)),3),
                            "confidence_basis": "HEURISTIC",
                            "method": "local_variance",
                            "bounding_box": [int(rx), int(ry), int(rw), int(rh)],
                            "evidence_id": "E-AAD-F1",
                            "page": 1
                        })

        # 2. Sharpness inconsistency
        if sharp_map:
            laps = [lap for (_, lap) in sharp_map]
            mean_lap = np.mean(laps)
            std_lap = np.std(laps)
            if std_lap > mean_lap*0.8 and mean_lap>10:
                signals.append(f"Local sharpness variance elevated (std {std_lap:.1f} vs mean {mean_lap:.1f})")
                # Find blocks with very high sharpness outlier (possible paste)
                high_sharp = [ (x,y) for ((x,y), lap) in sharp_map if lap > mean_lap + 2.5*std_lap]
                if len(high_sharp) >= 2 and len(high_sharp) <= 15:
                    xs = [x for x,y in high_sharp]
                    ys = [y for x,y in high_sharp]
                    rx, ry = min(xs), min(ys)
                    rw, rh = max(xs)-rx+block_size, max(ys)-ry+block_size
                    is_qr_area = (rx > w*0.65 and ry < h*0.4)
                    if not is_qr_area and rw>40 and rh>40:
                        # Avoid duplicate region
                        if not any(r["method"]=="local_sharpness" for r in regions):
                            regions.append({
                                "region_id": "FOR-002",
                                "reason": "Localized sharpness inconsistency - possible inserted region",
                                "severity": "MEDIUM",
                                "confidence": 0.65,
                                "confidence_basis": "HEURISTIC",
                                "method": "local_sharpness",
                                "bounding_box": [int(rx), int(ry), int(rw), int(rh)],
                                "evidence_id": "E-AAD-F2",
                                "page": 1
                            })

        # 3. ELA-like: JPEG recompression detection via error level
        # We simulate ELA by recompressing at 90 quality and diff
        try:
            encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), 90]
            _, enc = cv2.imencode('.jpg', image, encode_param)
            recompressed = cv2.imdecode(enc, cv2.IMREAD_COLOR)
            if recompressed is not None:
                diff = cv2.absdiff(image, recompressed)
                diff_gray = cv2.cvtColor(diff, cv2.COLOR_BGR2GRAY)
                mean_diff = float(np.mean(diff_gray))
                max_diff = float(np.max(diff_gray))
                # ELA score heuristic: high max diff with low mean suggests localized high error
                ela_score = float(max_diff - mean_diff)
                if ela_score > 70 and mean_diff < 20:
                    signals.append(f"Recompression-like localized high error detected (ELA-like score {ela_score:.1f})")
                    # Find region with high diff
                    _, thresh = cv2.threshold(diff_gray, max(35, int(mean_diff+max_diff*0.35)), 255, cv2.THRESH_BINARY)
                    # Find contours
                    contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
                    # Filter large contours not covering whole image
                    for i, cnt in enumerate(contours[:3]):
                        x,y,wc,hc = cv2.boundingRect(cnt)
                        area = wc*hc
                        is_qr_area = (x > w*0.65 and y < h*0.4)
                        if not is_qr_area and area < 0.35*h*w and area > 800:
                            regions.append({
                                "region_id": f"FOR-ELA-{i+1:02d}",
                                "reason": "Recompression artifact hotspot - possible edited area",
                                "severity": "MEDIUM",
                                "confidence": 0.6,
                                "confidence_basis": "HEURISTIC",
                                "method": "ela_like",
                                "bounding_box": [int(x),int(y),int(wc),int(hc)],
                                "evidence_id": f"E-AAD-ELA{i+1}",
                                "page": 1
                            })
                            break
                else:
                    ela_score = float(mean_diff)
                recompression_detected = ela_score > 60
            else:
                ela_score = None
                recompression_detected = False
        except Exception as e:
            ela_score = None
            recompression_detected = False
            notes.append(f"ELA error: {e}")

        # 4. Check photo region anomaly separately if fields provided? Could compare photo region texture
        # For now generic

        # 5. Edge discontinuity? Use Canny edge density per block - similar to noise

        overall_label = "SUSPICIOUS" if (signals and len(regions)>=1) else ("NO_SIGNIFICANT_SIGNAL" if not signals else "LOW_SIGNAL")
        # If many signals but no region, keep as low_signal
        # Provide noise_score etc
        noise_score = float(np.mean(block_means)) if block_means else None
        sharpness_variance = float(np.std(laps)) if sharp_map else None

        if not signals:
            notes.append("No significant forensic inconsistency detected.")

        return {
            "analyzed": True,
            "signals": signals,
            "regions": regions,
            "ela_score": ela_score,
            "noise_score": noise_score,
            "sharpness_variance": sharpness_variance,
            "recompression_detected": recompression_detected,
            "overall_label": overall_label,
            "notes": "; ".join(notes) if notes else "; ".join(signals) if signals else "No significant signal"
        }

    except Exception as e:
        return {
            "analyzed": False,
            "signals": [f"Forensic analysis error: {e}"],
            "regions": [],
            "ela_score": None,
            "noise_score": None,
            "sharpness_variance": None,
            "recompression_detected": False,
            "overall_label": "ERROR",
            "notes": str(e)
        }

def generate_annotated_image(image, regions):
    if image is None:
        return None, None
    annotated = image.copy()
    for r in regions:
        x,y,w,h = r["bounding_box"]
        # draw box red
        cv2.rectangle(annotated, (x,y), (x+w, y+h), (0,0,255), 2)
        label = r["region_id"]
        cv2.putText(annotated, label, (x, y-5), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0,0,255), 1, cv2.LINE_AA)
    return annotated, regions
