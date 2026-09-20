import io
from PIL import Image
from PIL.ExifTags import TAGS

def analyze_metadata(data: bytes, file_type: str, image=None):
    exif = {}
    software_tags=[]
    signals=[]
    editing_detected=False
    notes = []
    try:
        # Use Pillow to read exif
        pil = Image.open(io.BytesIO(data))
        info = pil.info
        # exif
        exif_data = pil.getexif()
        if exif_data:
            for tag_id, value in exif_data.items():
                tag = TAGS.get(tag_id, tag_id)
                try:
                    # Truncate large values
                    val_str = str(value)[:200]
                    exif[str(tag)] = val_str
                    # check software
                    if "software" in str(tag).lower() or "make" in str(tag).lower():
                        software_tags.append(val_str)
                        if any(s.lower() in val_str.lower() for s in ["photoshop","gimp","paint","editor","illustrator"]):
                            editing_detected = True
                            signals.append("Editing software metadata detected.")
                except:
                    continue
        # info dict
        for k,v in info.items():
            if k.lower() in ["software","creation time","modification time","comment","exif","icc_profile"]:
                software_tags.append(f"{k}: {str(v)[:100]}")
        # dimensions
        dimensions = f"{pil.width}x{pil.height}" if hasattr(pil,'width') else None

        # check for missing metadata (not suspicious)
        if not exif_data or len(exif_data)==0:
            notes.append("No EXIF metadata present. This is common for screenshots and compressed images and is not by itself suspicious.")
        else:
            notes.append(f"EXIF entries found: {len(exif_data)}")

        # Check if software tag indicates editing
        if editing_detected:
            signals.append("Image editing software tag found in metadata.")
            notes.append("Editing software tag does not automatically indicate manipulation but is considered supporting evidence.")
        else:
            if software_tags:
                notes.append(f"Software tags: {', '.join(software_tags[:3])}")
    except Exception as e:
        notes.append(f"Metadata analysis error: {e}")
        dimensions = None

    return {
        "exif": exif,
        "software_tags": software_tags[:10],
        "creation_metadata": None,
        "dimensions": dimensions,
        "file_type": file_type,
        "signals": signals,
        "editing_software_detected": editing_detected,
        "notes": "; ".join(notes) if notes else None
    }
