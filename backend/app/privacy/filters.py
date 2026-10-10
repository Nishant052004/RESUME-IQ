"""Bias-aware screening helpers (Module 5).

1. Protected-attribute scrubbing — lines revealing gender, age, religion,
   caste, marital status, nationality etc. are dropped from the text *before*
   extraction and scoring, so no personal attribute can influence the rank.
2. Transparency logging — every match result ships the exact criteria and
   weights used, so recruiters can audit how the score was computed.
"""
import re

from ..extraction.lexicon import PROTECTED_ATTRIBUTE_HINTS

# A line that *starts with* a protected-attribute label, e.g. "Gender: Female"
# or "Date of Birth - 14/03/1995". Anchoring at line start keeps ordinary
# sentences ("Used age-appropriate design patterns") untouched.
PROTECTED_LINE_RE = re.compile(
    r"^\s*(" + "|".join(PROTECTED_ATTRIBUTE_HINTS) + r")\b\s*[:\-][^\n]*$",
    re.IGNORECASE,
)


def strip_protected_attributes(text: str) -> str:
    """Remove self-identified protected attributes from resume text."""
    kept = []
    for line in text.splitlines():
        if PROTECTED_LINE_RE.match(line):
            continue
        kept.append(line)
    return "\n".join(kept)


def scoring_criteria(weights: dict, jd_profile: dict) -> list[str]:
    """Human-readable description of the exact scoring criteria in effect."""
    criteria = [
        f"Skills coverage of the job requirements — weight {weights.get('skills', 0):.0%}",
        f"Relevant experience vs. required {jd_profile.get('min_years_experience', 0)} year(s) — weight {weights.get('experience', 0):.0%}",
        f"Project relevance to this job description — weight {weights.get('projects', 0):.0%}",
        f"Education vs. required degrees — weight {weights.get('education', 0):.0%}",
        f"Certifications — weight {weights.get('certifications', 0):.0%}",
    ]
    active = [c for c in criteria if not c.endswith("weight 0%")]
    return active + [
        "Protected attributes (gender, age, religion, caste, marital status, nationality) "
        "are excluded from scoring by design.",
        "Semantic similarity is computed on job-related text only (alias-normalized TF-IDF).",
    ]
