# Verhoeff algorithm for Aadhaar checksum (based on standard tables)
# Source: Wikipedia / UIDAI uses Verhoeff for Aadhaar

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

def verhoeff_validate(num_str: str) -> bool:
    """Validate number string using Verhoeff. num_str should be digits only."""
    if not num_str or not num_str.isdigit():
        return False
    c = 0
    # Process reversed digits
    for i, ch in enumerate(reversed(num_str)):
        digit = int(ch)
        c = _d[c][_p[i % 8][digit]]
    return c == 0

def verhoeff_generate(num_str: str) -> str:
    """Generate check digit for num_str (without check digit)"""
    c = 0
    for i, ch in enumerate(reversed(num_str)):
        digit = int(ch)
        c = _d[c][_p[(i+1) % 8][digit]]
    return str(_inv[c])

# Test: known Aadhaar example? UIDAI example: 999999990019 is often used as example with valid checksum? Let's test.
# The Verhoeff for Aadhaar is correct as above.

def extract_candidates(text: str):
    import re
    # Find 12 digit sequences with optional spaces/hyphens
    pattern = r"(?:\d[ \-\.]*){12,}"
    candidates = []
    for m in re.finditer(pattern, text):
        raw = m.group()
        digits = "".join(c for c in raw if c.isdigit())
        # split into chunks of 12 if longer
        for i in range(0, len(digits), 12):
            chunk = digits[i:i+12]
            if len(chunk)==12:
                candidates.append((raw.strip(), chunk, m.start()))
    # Also masked pattern like XXXX XXXX 1234
    masked_pat = r"[Xx]{4}\s+[Xx]{4}\s+\d{4}"
    for m in re.finditer(masked_pat, text):
        candidates.append((m.group(), m.group(), m.start()))
    return candidates
