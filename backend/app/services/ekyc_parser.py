import zipfile
import xml.etree.ElementTree as ET
import io
from pathlib import Path

def parse_offline_ekyc(file_path: Path, data: bytes):
    result = {
        "provided": True,
        "status": "NOT_PROVIDED",
        "fields": {},
        "signature_status": "NOT_CHECKED",
        "signature_message": None,
        "consistency": None,
        "notes": None
    }
    if not file_path or not data:
        result["provided"] = False
        result["status"] = "NOT_PROVIDED"
        return result

    try:
        ext = file_path.suffix.lower()
        xml_content = None
        if ext == ".zip":
            try:
                z = zipfile.ZipFile(io.BytesIO(data))
                # find xml inside
                xml_name = None
                for info in z.infolist():
                    if info.filename.lower().endswith(".xml"):
                        xml_name = info.filename
                        break
                if not xml_name:
                    result["status"] = "FAILED"
                    result["notes"] = "No XML found inside ZIP"
                    return result
                xml_content = z.read(xml_name)
                # xml may be bytes
                if isinstance(xml_content, bytes):
                    xml_content = xml_content.decode("utf-8", errors="ignore")
            except Exception as e:
                result["status"] = "FAILED"
                result["notes"] = f"ZIP extraction failed: {e}"
                return result
        elif ext == ".xml":
            xml_content = data.decode("utf-8", errors="ignore") if isinstance(data, bytes) else data
        else:
            result["status"] = "FAILED"
            result["notes"] = "Unsupported eKYC file type"
            return result

        if not xml_content or len(xml_content.strip()) < 10:
            result["status"] = "FAILED"
            result["notes"] = "Empty XML content"
            return result

        # Try parse XML
        try:
            root = ET.fromstring(xml_content.encode("utf-8") if isinstance(xml_content,str) else xml_content)
            # Look for OfflinePaperlessKyc or similar
            fields = {}
            # Common attributes at root or child
            # Extract from attributes
            for elem in root.iter():
                # Check tag like UidData
                tag = elem.tag
                # If tag contains 'UidData'
                attribs = elem.attrib
                for k,v in attribs.items():
                    kl = k.lower()
                    if kl in ["uid","name","gender","dob","yob","co","house","street","vtc","dist","state","pc","phone","email","photo"]:
                        fields[kl] = v
                # Text content? child Poi, Poa?
                if tag.endswith("Poi"):
                    for k,v in attribs.items():
                        fields[k.lower()] = v
                if tag.endswith("Poa"):
                    for k,v in attribs.items():
                        # address fields
                        fields[k.lower()] = v
                if tag.endswith("Pht"):
                    # photo base64?
                    if elem.text and len(elem.text.strip())>100:
                        fields["photo_present"] = True
                        fields["photo_length"] = len(elem.text.strip())
                    else:
                        # maybe attribute
                        if "pht" in attribs:
                            fields["photo_present"] = True

            # Fallback: search via string regex if XML parsing gave little
            if len(fields)<2:
                import re
                # uid
                m = re.search(r'uid=["\']([^"\']+)["\']', xml_content)
                if m:
                    fields["uid"] = m.group(1)
                m = re.search(r'name=["\']([^"\']+)["\']', xml_content, re.IGNORECASE)
                if m:
                    fields["name"] = m.group(1)
                m = re.search(r'gender=["\']([MF])["\']', xml_content, re.IGNORECASE)
                if m:
                    fields["gender"] = {"M":"MALE","F":"FEMALE"}.get(m.group(1).upper(), m.group(1))
                m = re.search(r'dob=["\']([^"\']+)["\']', xml_content, re.IGNORECASE)
                if m:
                    fields["dob"] = m.group(1)
                m = re.search(r'yob=["\'](\d{4})["\']', xml_content, re.IGNORECASE)
                if m:
                    fields["yob"] = m.group(1)

            if not fields:
                fields["raw_preview"] = xml_content[:500]
                fields["note"] = "XML structure not recognized, raw preview stored"

            result["fields"] = fields
            result["status"] = "PARSED"
            result["notes"] = f"Parsed {len(fields)} fields from eKYC XML"
            # Signature status placeholder - real verification requires cert
            result["signature_status"] = "NOT_CONFIGURED"
            result["signature_message"] = "Cryptographic verification not configured. Offline eKYC signature verification requires official UIDAI certificate."

        except ET.ParseError as e:
            result["status"] = "FAILED"
            result["notes"] = f"XML parsing failed: {e}"
            return result

    except Exception as e:
        result["status"] = "FAILED"
        result["notes"] = f"eKYC parsing error: {e}"

    return result
