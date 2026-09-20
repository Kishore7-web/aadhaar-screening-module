import time
import fitz  # PyMuPDF
import cv2
import numpy as np
from pathlib import Path
from PIL import Image
import io
from ..utils.hashing import sha256_bytes

def load_document(tmp_path: Path, data: bytes):
    start = time.time()
    info = {
        "file_type": tmp_path.suffix.lower().lstrip("."),
        "mime_type": None,
        "page_count": 1,
        "pages_analyzed": 1,
        "sha256": sha256_bytes(data),
        "width": None,
        "height": None,
        "pages": []
    }
    images = []
    errors=[]
    try:
        suffix = tmp_path.suffix.lower()
        if suffix == ".pdf":
            info["mime_type"] = "application/pdf"
            doc = fitz.open(str(tmp_path))
            info["page_count"] = len(doc)
            # limit pages
            max_pages = 5
            pages_to_render = min(len(doc), max_pages)
            info["pages_analyzed"] = pages_to_render
            for i in range(pages_to_render):
                page = doc[i]
                # render at 200 dpi
                pix = page.get_pixmap(dpi=200)
                img_data = pix.tobytes("png")
                arr = np.frombuffer(img_data, np.uint8)
                img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
                if img is not None:
                    images.append({"image": img, "page": i+1, "width": img.shape[1], "height": img.shape[0]})
                    info["pages"].append({"page": i+1, "width": img.shape[1], "height": img.shape[0], "text_layer": bool(page.get_text().strip())})
                else:
                    errors.append({"stage":"document_loader","message":f"Failed to render page {i+1}"})
            doc.close()
            # dimensions from first page
            if images:
                info["width"] = images[0]["width"]
                info["height"] = images[0]["height"]
        else:
            # image
            if suffix in [".jpg",".jpeg"]:
                info["mime_type"] = "image/jpeg"
            elif suffix == ".png":
                info["mime_type"] = "image/png"
            arr = np.frombuffer(data, np.uint8)
            img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
            if img is None:
                # PIL fallback
                pil = Image.open(io.BytesIO(data)).convert("RGB")
                img = cv2.cvtColor(np.array(pil), cv2.COLOR_RGB2BGR)
            if img is None:
                errors.append({"stage":"document_loader","message":"Failed to decode image"})
                return None, info, errors
            info["width"] = img.shape[1]
            info["height"] = img.shape[0]
            info["page_count"] = 1
            info["pages_analyzed"] = 1
            images.append({"image": img, "page": 1, "width": img.shape[1], "height": img.shape[0]})
            info["pages"].append({"page":1, "width": img.shape[1], "height": img.shape[0], "text_layer": False})
    except Exception as e:
        errors.append({"stage":"document_loader","message":str(e)})
        return None, info, errors

    duration = int((time.time() - start)*1000)
    info["load_duration_ms"] = duration
    return images, info, errors
