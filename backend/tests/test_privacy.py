"""Module 5 tests — PII redaction & bias-aware filtering."""
from app.privacy.filters import scoring_criteria, strip_protected_attributes
from app.privacy.pii import detect_pii, redact_text

PII_RESUME = """Anita Desai
Email: anita.desai@example.com
Phone: +91 98765 43210
Alt: 98200-11234
Aadhaar: 1234 5678 9012
DOB: 14/03/1995
Flat 402, Rose Apartment, MG Road, Bengaluru 560001

SUMMARY
Backend developer with 4 years of experience.
"""


def test_detects_common_pii_types():
    kinds = {s["type"] for s in detect_pii(PII_RESUME)}
    assert {"email", "phone", "government_id", "date_of_birth"} <= kinds


def test_redaction_removes_every_pii_value():
    redacted = redact_text(PII_RESUME)
    assert "anita.desai@example.com" not in redacted
    assert "98765 43210" not in redacted
    assert "98200-11234" not in redacted
    assert "1234 5678 9012" not in redacted
    assert "14/03/1995" not in redacted
    assert "[REDACTED-EMAIL]" in redacted
    assert "[REDACTED-PHONE]" in redacted


def test_redaction_preserves_non_pii_text():
    redacted = redact_text("Built FastAPI services with PostgreSQL and Docker in 2021-2023")
    assert "FastAPI" in redacted and "2021-2023" in redacted


def test_date_ranges_are_not_treated_as_phone_numbers():
    spans = detect_pii("Worked there from 2019 - 2022 and 2020 to 2021")
    assert not any(s["type"] == "phone" for s in spans)


def test_protected_attribute_lines_are_stripped():
    text = """Kiran Rao
Gender: Female
Age: 34 years
Marital Status: Married
Religion: Hindu
Caste: OBC
Nationality: Indian

SUMMARY
Backend developer with 5 years of experience in Python.
"""
    stripped = strip_protected_attributes(text)
    for hint in ("Gender", "Age:", "Marital", "Religion", "Caste", "Nationality"):
        assert hint not in stripped
    assert "Python" in stripped and "Kiran Rao" in stripped


def test_regular_lines_survive_stripping():
    text = "EXPERIENCE\nUsed age-appropriate design patterns\nSKILLS\nPython"
    assert "age-appropriate" in strip_protected_attributes(text)


def test_scoring_criteria_transparency_output():
    criteria = scoring_criteria({"skills": 40, "experience": 25, "projects": 15, "education": 10, "certifications": 10},
                                {"min_years_experience": 3})
    assert any("3 year" in c for c in criteria)
    assert any("Protected attributes" in c for c in criteria)
