"""Information extraction engine (Module 2).

Turns raw resume/JD text into a structured JSON profile using a hybrid of
regex rules, section parsing and the skill lexicon in `lexicon.py`. When an
LLM API key is configured the same profile can optionally be refined by the
LLM (`llm_refine`), but the deterministic engine works fully offline.
"""
import re
from datetime import datetime

from .lexicon import ALIAS_INDEX, CERTIFICATION_PATTERNS, IMPLIES, LEXICON

MONTHS = {
    "jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
    "jul": 7, "aug": 8, "sep": 9, "sept": 9, "oct": 10, "nov": 11, "dec": 12,
}

SECTION_HEADINGS = {
    "summary": r"summary|objective|profile|about me",
    "experience": r"(?:work\s+|professional\s+|employment\s+)?experience|employment|work\s+history|internships?",
    "education": r"education|academics?",
    "skills": r"(?:technical\s+)?skills|technologies|tech\s+stack",
    "projects": r"(?:personal\s+|academic\s+|key\s+)?projects?",
    "certifications": r"certifications?|certificates?|licenses?|courses?",
    "achievements": r"achievements?|awards?|accomplishments?",
    "languages": r"languages?\s+known|spoken\s+languages?",
    "interests": r"interests?|hobbies",
}

EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
PHONE_RE = re.compile(r"(?:\+?\d{1,3}[\s.-]?)?(?:\(?\d{2,4}\)?[\s.-]?){1,3}\d{2,4}")
DATE_RANGE_RE = re.compile(
    r"(?:(jan|feb|mar|apr|may|jun|jul|aug|sep|sept|oct|nov|dec)[a-z]*\.?\s*)?(\d{4})\s*(?:-|–|—|to|until)\s*"
    r"(?:(jan|feb|mar|apr|may|jun|jul|aug|sep|sept|oct|nov|dec)[a-z]*\.?\s*)?(\d{4}|present|current|till\s*date|now|date)",
    re.IGNORECASE,
)
DEGREE_RE = re.compile(
    r"(b\.?tech|b\.?e\b|b\.?sc|b\.?ca|b\.?com|b\.?a\b|bachelor(?:'s)?(?:\s+of)?(?:\s+\w+)?"
    r"|m\.?tech|m\.?e\b|m\.?sc|m\.?ca|m\.?com|m\.?a\b|master(?:'s)?(?:\s+of)?(?:\s+\w+)?"
    r"|mba|ph\.?d|doctorate|diploma|class\s+(?:x{1,2}i?|1[0-2])|1[02]th)",
    re.IGNORECASE,
)


def split_sections(text: str) -> dict[str, str]:
    """Split resume text into known sections. Unknown text falls under `_body`."""
    sections: dict[str, str] = {}
    current = "_body"
    lines = text.splitlines()
    buckets: dict[str, list[str]] = {current: []}
    for line in lines:
        stripped = line.strip().rstrip(":").strip()
        if stripped and len(stripped) <= 60:
            for key, pattern in SECTION_HEADINGS.items():
                # A heading line is (almost) exactly the heading keyword.
                if re.fullmatch(pattern, stripped, re.IGNORECASE):
                    current = key
                    buckets.setdefault(current, [])
                    break
            else:
                buckets[current].append(line)
        else:
            buckets[current].append(line)
    for key, lines_ in buckets.items():
        content = "\n".join(lines_).strip()
        if content:
            sections[key] = content
    return sections


def canonical_skill(token: str) -> str | None:
    return ALIAS_INDEX.get(token.strip().lower())


def _skill_regex(alias: str) -> re.Pattern:
    return re.compile(r"(?<![A-Za-z0-9+#./])" + re.escape(alias) + r"(?![A-Za-z0-9+#.])", re.IGNORECASE)


def find_skills(text: str) -> dict[str, list[str]]:
    """Find canonical skills per category. Longer aliases are matched first so
    'rest api' wins over 'api'-style substrings and 'react native' over 'react'.
    Implied basics are added too (PostgreSQL → SQL, FastAPI → Python, ...)."""
    found: dict[str, dict[str, None]] = {}
    for category, skills in LEXICON.items():
        for canonical, aliases in skills.items():
            variants = [canonical] + list(aliases)
            variants.sort(key=len, reverse=True)
            for variant in variants:
                if _skill_regex(variant).search(text):
                    found.setdefault(category, {})[canonical] = None
                    break
    # Expand implications until stable (max 2 hops).
    technical = found.get("technical", {})
    for _ in range(2):
        additions = {
            implied
            for skill in technical
            for implied in IMPLIES.get(skill, [])
            if implied not in technical
        }
        if not additions:
            break
        for skill in additions:
            technical[skill] = None
    return {cat: list(skills) for cat, skills in found.items()}


def sentences(text: str) -> list[str]:
    parts = re.split(r"[\n•·]|(?<=[.;])\s+", text)
    return [p.strip(" -–•") for p in parts if p and len(p.strip()) > 3]


def skill_evidence(text: str, skills: list[str], per_skill: int = 2) -> dict[str, list[str]]:
    """Quote up to `per_skill` resume sentences mentioning each skill."""
    evidence: dict[str, list[str]] = {}
    for skill in skills:
        variants = [skill] + LEXICON.get("technical", {}).get(skill, [])
        variants += [a for a, c in ALIAS_INDEX.items() if c == skill and a != skill]
        variants.sort(key=len, reverse=True)
        hits: list[str] = []
        for sentence in sentences(text):
            low = sentence.lower()
            if any(_skill_regex(v).search(low) for v in variants):
                hits.append(sentence.strip()[:240])
            if len(hits) >= per_skill:
                break
        if hits:
            evidence[skill] = hits
    return evidence


def _month_index(mon: str | None, year: str) -> int:
    y = int(year)
    m = MONTHS.get((mon or "jan").lower()[:3], 1) if mon else 1
    if (mon or "").lower().startswith("sept"):
        m = 9
    return y * 12 + (m - 1)


def extract_experience(text: str, sections: dict[str, str]) -> dict:
    """Parse date ranges to estimate total experience and roles."""
    scope = sections.get("experience") or text
    intervals: list[tuple[int, int]] = []
    now = datetime.now()
    now_idx = now.year * 12 + now.month - 1
    for match in DATE_RANGE_RE.finditer(scope):
        m1, y1, m2, y2 = match.groups()
        if y2.lower() in ("present", "current", "now", "date") or y2.lower().startswith("till"):
            end = now_idx
        else:
            end = _month_index(m2, y2)
        start = _month_index(m1, y1)
        if 1970 * 12 <= start <= end <= now_idx + 1:
            intervals.append((start, end))

    merged: list[list[int]] = []
    for start, end in sorted(intervals):
        if merged and start <= merged[-1][1]:
            merged[-1][1] = max(merged[-1][1], end)
        else:
            merged.append([start, end])
    total_months = sum(end - start for start, end in merged)
    total_years = round(total_months / 12, 1)

    roles = []
    for chunk in re.split(r"\n(?=\S)", scope):
        m = DATE_RANGE_RE.search(chunk)
        if not m:
            continue
        first = chunk.strip().splitlines()[0][:120]
        title_part = re.sub(DATE_RANGE_RE, "", first).strip(" -–—|·,")
        title, company = "", ""
        if "|" in title_part:
            title, company = (p.strip() for p in title_part.split("|", 1))
        elif " at " in title_part.lower():
            title, company = (p.strip() for p in re.split(r" at ", title_part, maxsplit=1, flags=re.IGNORECASE))
        elif "," in title_part:
            title, company = (p.strip() for p in title_part.split(",", 1))
        else:
            title = title_part
        m1, y1, m2, y2 = m.groups()
        end_label = "Present" if (y2 or "").lower() not in tuple("0123456789") else y2
        roles.append({
            "title": title[:100],
            "company": company[:100],
            "period": f"{m1 or ''} {y1} – {end_label}".strip(),
        })
    return {"total_years": total_years, "roles": roles[:10]}


def extract_education(text: str, sections: dict[str, str]) -> list[dict]:
    scope = sections.get("education") or text
    out = []
    for line in scope.splitlines():
        m = DEGREE_RE.search(line)
        if not m:
            continue
        degree = m.group(0).strip()
        field_m = re.search(r"(?:in|of)\s+([A-Za-z&.,\s]{3,60})", line, re.IGNORECASE)
        field = field_m.group(1).strip(" .,") if field_m else ""
        inst_m = re.search(
            r"([A-Z][\w&.'\- ]*(?:university|college|institute|school|academy|iit|nit|iiit)[\w&.'\- ]*)",
            line,
        )
        out.append({
            "degree": degree.upper() if len(degree) <= 12 else degree.title(),
            "field": field.title()[:80],
            "institution": inst_m.group(1).strip()[:120] if inst_m else "",
            "line": line.strip()[:200],
        })
    return out[:8]


def extract_certifications(text: str, sections: dict[str, str]) -> list[str]:
    scope = "\n".join(s for key, s in sections.items() if key in ("certifications",))
    scope = scope or text
    found: list[str] = []
    for pattern in CERTIFICATION_PATTERNS:
        for m in re.finditer(pattern, scope, re.IGNORECASE):
            value = re.sub(r"\s+", " ", m.group(0)).strip()
            if value and value.lower() not in [f.lower() for f in found]:
                found.append(value[:120])
    return found[:10]


def extract_projects(sections: dict[str, str]) -> list[dict]:
    scope = sections.get("projects", "")
    projects = []
    for chunk in re.split(r"\n(?=\S)", scope)[1:] if scope else []:
        lines = [l.strip() for l in chunk.splitlines() if l.strip()]
        if not lines:
            continue
        title = lines[0].strip(" -–—•:")[:100]
        detail = " ".join(lines[1:])[:400]
        projects.append({"title": title, "detail": detail})
    return projects[:10]


def extract_achievements(text: str) -> list[str]:
    """Impact/achievement statements — lines that quantify results."""
    pattern = re.compile(
        r"\b(improv\w+|increas\w+|reduc\w+|boost\w+|optimi[sz]\w+|sav\w+|grew\w+|scal\w+|achiev\w+|delivered|automat\w+)\b[^\n]{0,140}",
        re.IGNORECASE,
    )
    seen, out = set(), []
    for m in pattern.finditer(text):
        value = re.sub(r"\s+", " ", m.group(0)).strip()
        key = value.lower()[:60]
        if key not in seen:
            seen.add(key)
            out.append(value[:180])
        if len(out) >= 8:
            break
    return out


def guess_name(text: str) -> str:
    for line in text.splitlines()[:6]:
        candidate = line.strip()
        if not candidate or len(candidate) > 48:
            continue
        if re.search(r"[\d@_/,]|resume|curriculum", candidate, re.IGNORECASE):
            continue
        words = candidate.split()
        if 1 < len(words) <= 4 and all(w.isalpha() or "." in w for w in words):
            return candidate
    return ""


def build_resume_profile(text: str) -> dict:
    sections = split_sections(text)
    skills = find_skills(text)
    # Spoken languages should come from the languages/summary area when present,
    # to avoid counting 'english' in a JD-quoted sentence.
    lang_scope = "\n".join(s for k, s in sections.items() if k in ("languages", "summary", "_body"))
    skills["languages_spoken"] = find_skills(lang_scope if lang_scope.strip() else text).get("languages_spoken", [])
    all_technical = skills.get("technical", [])
    return {
        "name": guess_name(text),
        "contact": {
            "emails": list(dict.fromkeys(EMAIL_RE.findall(text)))[:3],
            "phones": [p.strip() for p in PHONE_RE.findall(text) if len(re.sub(r"\D", "", p)) >= 10][:3],
        },
        "skills": skills,
        "certifications": extract_certifications(text, sections),
        "experience": extract_experience(text, sections),
        "education": extract_education(text, sections),
        "projects": extract_projects(sections),
        "achievements": extract_achievements(text),
        "sections": sections,
        "skill_evidence": skill_evidence(text, all_technical + skills.get("soft", [])),
    }


NICE_TO_HAVE_MARKERS = re.compile(
    r"nice\s*to\s+have|good\s*to\s+have|preferred|bonus|plus[s]?\s*:|desirable|optional", re.IGNORECASE
)


def build_jd_profile(text: str) -> dict:
    """Extract structured requirements from a job description."""
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    title = ""
    for line in lines[:4]:
        clean = line.strip(" -–—#*")
        if clean and not EMAIL_RE.search(clean) and 3 < len(clean) <= 80:
            title = clean
            break

    # Split the JD into a must-have part and a nice-to-have part.
    nice_start = None
    for m in NICE_TO_HAVE_MARKERS.finditer(text):
        nice_start = m.start()
        break
    must_text, nice_text = (text[:nice_start], text[nice_start:]) if nice_start else (text, "")

    must_skills = find_skills(must_text).get("technical", [])
    nice_skills = [s for s in find_skills(nice_text).get("technical", []) if s not in must_skills]

    min_years = 0
    for m in re.finditer(r"(\d{1,2})\s*\+?\s*(?:-|–|to)?\s*(\d{1,2})?\s*\+?\s*years?", text, re.IGNORECASE):
        candidate = int(m.group(1))
        if 0 < candidate <= 20:
            min_years = max(min_years, candidate)

    education = sorted({m.group(0).upper() for m in DEGREE_RE.finditer(text)}, key=len)[:4]
    return {
        "title": title or "Untitled role",
        "must_have_skills": must_skills,
        "nice_to_have_skills": nice_skills,
        "min_years_experience": min_years,
        "education": education,
        "certifications": extract_certifications(text, {}),
        "responsibilities": sentences(text)[:12],
        "skill_evidence": skill_evidence(text, must_skills + nice_skills),
    }
