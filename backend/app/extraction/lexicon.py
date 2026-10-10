"""Skill lexicon with alias → canonical mapping (Module 2).

Powers related-term/semantic-ish matching: "React.js" ↔ React, "Postgres" ↔
PostgreSQL, "K8s" ↔ Kubernetes, etc. Each canonical skill may carry several
surface aliases; matching is done on word boundaries, case-insensitively.
"""

LEXICON: dict[str, dict[str, list[str]]] = {
    "technical": {
        "python": ["python3"],
        "java": ["java 8", "java8", "core java"],
        "javascript": ["js", "es6", "ecmascript"],
        "typescript": ["ts"],
        "c++": ["cpp", "c plus plus"],
        "c#": ["csharp", "c sharp"],
        "go": ["golang"],
        "sql": [],
        "react": ["react.js", "reactjs", "react js"],
        "react native": ["react-native"],
        "next.js": ["nextjs", "next js"],
        "node.js": ["nodejs", "node js", "node"],
        "express": ["express.js", "expressjs"],
        "angular": ["angularjs"],
        "vue.js": ["vuejs", "vue js", "vue"],
        "fastapi": ["fast api"],
        "django": [],
        "flask": [],
        "spring boot": ["springboot", "spring"],
        ".net": ["dotnet", "asp.net"],
        "php": ["laravel"],
        "ruby": ["ruby on rails", "rails"],
        "kotlin": [],
        "swift": [],
        "html": ["html5"],
        "css": ["css3"],
        "tailwind css": ["tailwind", "tailwindcss"],
        "rest api": ["rest", "restful", "rest apis", "restful apis"],
        "graphql": [],
        "websockets": ["websocket"],
        "redux": ["redux toolkit"],
        "machine learning": ["ml"],
        "deep learning": [],
        "nlp": ["natural language processing"],
        "computer vision": [],
        "generative ai": ["gen ai", "genai", "llm", "llms", "large language models"],
        "embeddings": ["vector embeddings", "semantic search"],
        "pandas": [],
        "numpy": [],
        "scikit-learn": ["sklearn", "scikit learn"],
        "tensorflow": [],
        "pytorch": [],
        "keras": [],
        "langchain": [],
        "data analysis": ["data analytics", "analytics"],
        "power bi": ["powerbi"],
        "tableau": [],
        "postgresql": ["postgres", "psql"],
        "mysql": [],
        "mongodb": ["mongo"],
        "redis": [],
        "sqlite": [],
        "elasticsearch": [],
        "chromadb": ["chroma db", "chroma"],
        "faiss": [],
        "aws": ["amazon web services", "ec2", "s3", "lambda"],
        "gcp": ["google cloud", "google cloud platform"],
        "azure": ["microsoft azure"],
        "docker": ["containerization", "containers"],
        "kubernetes": ["k8s"],
        "ci/cd": ["ci cd", "cicd", "continuous integration"],
        "jenkins": [],
        "github actions": ["githubactions"],
        "terraform": [],
        "linux": ["unix"],
        "nginx": [],
        "git": ["github", "gitlab", "version control"],
        "jira": [],
        "figma": [],
        "excel": ["microsoft excel"],
        "linux shell": ["bash", "shell scripting"],
    },
    "soft": {
        "communication": ["communication skills", "verbal communication"],
        "leadership": ["team lead", "led a team", "mentoring"],
        "teamwork": ["cross-functional", "collaboration", "collaborative"],
        "problem solving": ["problem-solving", "analytical thinking", "troubleshooting"],
        "time management": ["prioritization", "deadlines"],
        "adaptability": ["fast learner", "self-motivated"],
    },
    "languages_spoken": {
        "english": [],
        "hindi": [],
        "german": [],
        "french": [],
        "spanish": [],
        "mandarin": ["chinese"],
    },
}

# Flat alias → canonical index used by the matcher and extractor.
ALIAS_INDEX: dict[str, str] = {}
for _cat, _skills in LEXICON.items():
    for _canonical, _aliases in _skills.items():
        ALIAS_INDEX[_canonical.lower()] = _canonical
        for _a in _aliases:
            ALIAS_INDEX[_a.lower()] = _canonical

CANONICAL_SKILLS: set[str] = {c for _c, s in LEXICON.items() for c in s}

# Concept implication for related-term matching: finding the left-hand skill
# implies the candidate also has the right-hand basics (PostgreSQL → SQL,
# FastAPI → Python, React → JavaScript, ...). Used for resumes and JDs alike.
IMPLIES: dict[str, list[str]] = {
    "postgresql": ["sql"],
    "mysql": ["sql"],
    "sqlite": ["sql"],
    "oracle": [],  # not in the lexicon; kept for clarity
    "fastapi": ["python"],
    "django": ["python"],
    "flask": ["python"],
    "pandas": ["python"],
    "numpy": ["python"],
    "scikit-learn": ["python", "machine learning"],
    "tensorflow": ["python", "machine learning"],
    "pytorch": ["python", "machine learning"],
    "keras": ["python", "machine learning"],
    "langchain": ["python", "generative ai"],
    "spring boot": ["java"],
    "node.js": ["javascript"],
    "express": ["node.js", "javascript"],
    "react": ["javascript"],
    "react native": ["react", "javascript"],
    "next.js": ["react", "javascript"],
    "redux": ["react"],
    "tailwind css": ["css"],
    "chromadb": ["embeddings"],
    "faiss": ["embeddings"],
    "jenkins": ["ci/cd"],
    "github actions": ["ci/cd"],
    "terraform": ["aws"],
}
IMPLIES = {k: [v for v in vs if v in CANONICAL_SKILLS] for k, vs in IMPLIES.items()}

# Certification patterns are matched as regexes (not exact words).
CERTIFICATION_PATTERNS = [
    r"aws\s+certified[\w\s\-/]*",
    r"azure\s+certified[\w\s\-/]*",
    r"google\s+cloud\s+certified[\w\s\-/]*",
    r"professional\s+cloud\s+architect[\w\s\-/]*",
    r"\bpmp\b(?:\s*\(.*?\))?",
    r"certified\s+scrum\s+master\b|\bcsm\b",
    r"\bccna\b[\w\s\-/]*",
    r"\boci\s+certified[\w\s\-/]*",
    r"cisco\s+certified[\w\s\-/]*",
    r"microsoft\s+certified[\w\s\-/]*",
    r"tensorflow\s+developer\s+certificate[\w\s\-/]*",
    r"deep\.?ai\b[\w\s\-/]*",
    r"coursera[\w\s\-/]*specialization",
]

# Protected / personal attributes that must NEVER feed the score (Module 5).
PROTECTED_ATTRIBUTE_HINTS = [
    "gender", "male", "female", "age", "date of birth", "dob", "marital status",
    "married", "religion", "caste", "nationality", "photo", "father's name",
    "mother's name", "ethnicity", "disability",
]
