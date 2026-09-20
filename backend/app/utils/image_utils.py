import cv2
import numpy as np
from PIL import Image
import io

def load_image_from_bytes(data: bytes):
    arr = np.frombuffer(data, np.uint8)
    img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    if img is None:
        # try PIL
        try:
            pil = Image.open(io.BytesIO(data)).convert("RGB")
            img = cv2.cvtColor(np.array(pil), cv2.COLOR_RGB2BGR)
        except:
            return None
    return img

def estimate_blur(img):
    if img is None:
        return None
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    fm = cv2.Laplacian(gray, cv2.CV_64F).var()
    return float(fm)

def estimate_brightness_contrast(img):
    if img is None:
        return None, None
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    brightness = float(np.mean(gray))
    contrast = float(np.std(gray))
    return brightness, contrast

def detect_glare(img):
    if img is None:
        return False
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    # glare = many very bright pixels
    bright = np.sum(gray > 240) / gray.size
    return bright > 0.05

def resize_for_processing(img, max_dim=1200):
    h,w = img.shape[:2]
    if max(h,w) <= max_dim:
        return img
    scale = max_dim / max(h,w)
    new_w, new_h = int(w*scale), int(h*scale)
    return cv2.resize(img, (new_w, new_h), interpolation=cv2.INTER_AREA)

def preprocess_for_ocr(img):
    # Convert to grayscale, adaptive threshold, denoise
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    # CLAHE
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
    gray = clahe.apply(gray)
    # denoise
    # Note: fastNlMeansDenoising is heavy, use bilateral or median
    gray = cv2.medianBlur(gray, 3)
    return gray
