"""PII detection & redaction (Module 5).

Regex-based detection for the common identifiers, applied to resume text at
ingestion time when the recruiter's PII-redaction setting is ON (default).
Redaction happens *before* storage and before profile extraction, so PII never
reaches the database or the API responses.
"""
import re

EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
PHONE_RE = re.compile(r"(?:\+?\d{1,3}[\s.-]?)?(?:\(?\d{2,4}\)?[\s.-]?){1,3}\d{2,4}")
AADHAAR_RE = re.compile(r"\b\d{4}\s\d{4}\s\d{4}\b")
SSN_RE = re.compile(r"\b\d{3}-\d{2}-\d{4}\b")
DOB_RE = re.compile(
    r"\b(dob|d\.o\.b|date\s+of\s+birth|birth\s+date)\s*[:\-]?\s*"
    r"(\d{1,2}[/.-]\d{1,2}[/.-]\d{2,4}|\d{1,2}\s+[A-Za-z]{3,9},?\s+\d{4})",
    re.IGNORECASE,
)
ADDRESS_RE = re.compile(
    r"^\s*\d{0,5}\w?\s+[\w\s,#.-]{0,60}?"
    r"(street|st\.|road|rd\.|avenue|ave\.|lane|ln\.|nagar|sector|colony|apartment|apt\.?|flat|block|phase)\b[\w\s,./#-]{0,40}$",
    re.IGNORECASE,
)


def detect_pii(text: str) -> list[dict]:
    """Return detected PII as {type, value, start, end} spans."""
    spans: list[dict] = []

    def add(kind: str, match: re.Match, value: str | None = None):
        value = value if value is not None else match.group(0)
        spans.append({"type": kind, "value": value, "start": match.start(), "end": match.end()})

    for m in EMAIL_RE.finditer(text):
        add("email", m)
    for m in AADHAAR_RE.finditer(text):
        add("government_id", m)
    for m in SSN_RE.finditer(text):
        add("government_id", m)
    for m in DOB_RE.finditer(text):
        add("date_of_birth", m)
    for m in PHONE_RE.finditer(text):
        digits = re.sub(r"\D", "", m.group(0))
        if 10 <= len(digits) <= 14:
            add("phone", m)
    for line_match in ADDRESS_RE.finditer(text):
        line = line_match.group(0)
        # Only treat it as an address when it carries a house/plot number.
        if re.search(r"\d", line) and len(line.split()) <= 14:
            spans.append({"type": "address", "value": line.strip(), "start": line_match.start(), "end": line_match.end()})

    # Resolve overlaps: keep the longest span at any offset (email before phone,
    # DOB before phone, government ids before phone).
    spans.sort(key=lambda s: (s["start"], -(s["end"] - s["start"])))
    resolved: list[dict] = []
    for span in spans:
        if resolved and span["start"] < resolved[-1]["end"]:
            continue
        resolved.append(span)
    return resolved


def redact_text(text: str) -> str:
    """Replace every detected PII span with a typed placeholder."""
    placeholders = {
        "email": "[REDACTED-EMAIL]",
        "phone": "[REDACTED-PHONE]",
        "address": "[REDACTED-ADDRESS]",
        "date_of_birth": "[REDACTED-DOB]",
        "government_id": "[REDACTED-ID]",
    }
    out = text
    # Apply from the end so earlier offsets stay valid.
    for span in reversed(detect_pii(text)):
        out = out[: span["start"]] + placeholders.get(span["type"], "[REDACTED]") + out[span["end"] :]
    return out
