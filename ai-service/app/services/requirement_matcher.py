import re
from dataclasses import dataclass
from typing import Literal

from app.models.analysis import AnalyzeRequest, RequirementMatch
from app.services.embedding_service import cosine_similarity


EvidenceSource = Literal["experience", "project", "skills", "certification", "achievement", "candidate_context", "other", "missing"]


@dataclass
class AtomicRequirement:
    text: str
    category: str
    importance: Literal["high", "medium", "low"]
    aliases: list[str]
    semanticAnchor: str


@dataclass
class ResumeEvidence:
    text: str
    source: EvidenceSource
    categories: set[str]
    strength: float


CONCEPTS: dict[str, dict[str, object]] = {
    "ASP.NET Core / ASP.NET": {
        "category": "backend",
        "aliases": ["asp.net core", "asp net core", "asp.net", "asp net", ".net", "dotnet", "mvc", "razor"],
    },
    "C#": {"category": "backend", "aliases": ["c#", "c sharp"]},
    "Web API / REST API": {
        "category": "backend",
        "aliases": ["web api", "rest api", "restapi", "rest services", "apis", "api integration", "endpoint", "endpoints"],
    },
    "Entity Framework / ORM": {
        "category": "database",
        "aliases": ["entity framework", "ef core", "ef", "orm", "migrations", "repository"],
    },
    "LINQ": {"category": "database", "aliases": ["linq", "iqueryable", "ienumerable"]},
    "SQL / SQL Server": {
        "category": "database",
        "aliases": ["sql", "sql server", "ssms", "stored procedure", "query", "database", "dbms"],
    },
    "Database performance tuning": {
        "category": "database",
        "aliases": ["indexing", "indexes", "query optimization", "execution plan", "performance tuning", "page load", "optimized sql"],
    },
    "Angular": {"category": "frontend", "aliases": ["angular"]},
    "React": {"category": "frontend", "aliases": ["react", "reactjs"]},
    "Frontend API integration": {
        "category": "frontend",
        "aliases": ["frontend integration", "api integration", "forms", "validation", "ui", "screen", "razor ui"],
    },
    "JavaScript / HTML / CSS": {
        "category": "frontend",
        "aliases": ["javascript", "js", "jquery", "html", "css", "typescript"],
    },
    "Azure cloud": {
        "category": "cloud_devops",
        "aliases": ["azure", "azure cloud", "app service", "azure sql", "key vault", "cloud basics", "cloud fundamentals"],
    },
    "CI/CD / Azure DevOps": {
        "category": "cloud_devops",
        "aliases": ["azure devops", "ci/cd", "pipeline", "pipelines", "deployment", "release", "build"],
    },
    "Docker / containers": {
        "category": "cloud_devops",
        "aliases": ["docker", "container", "containers", "kubernetes"],
    },
    "Authentication / Authorization": {
        "category": "security",
        "aliases": ["jwt", "authentication", "authorization", "oauth", "role", "policy", "security"],
    },
    "Production debugging": {
        "category": "debugging_reliability",
        "aliases": ["production", "debugging", "debug", "logs", "monitoring", "incident", "root cause", "support", "live issues", "traces"],
    },
    "System design basics": {
        "category": "system_design",
        "aliases": ["system design", "architecture", "scalable", "caching", "queue", "distributed", "pagination", "reliability"],
    },
    "DSA / problem solving": {
        "category": "problem_solving",
        "aliases": ["dsa", "leetcode", "codechef", "geeksforgeeks", "hackerRank", "problem solving", "competitive coding"],
    },
    "Project ownership": {
        "category": "ownership",
        "aliases": ["end-to-end", "ownership", "owned", "delivered", "requirements", "feature", "critical screens"],
    },
    "Cloud certification / basics": {
        "category": "cloud_devops",
        "aliases": ["certification", "certified", "certificate", "az-900", "cloud practitioner", "digital leader", "fundamentals"],
    },
}

SECTION_TO_SOURCE: dict[str, EvidenceSource] = {
    "experience": "experience",
    "projects": "project",
    "skills": "skills",
    "certifications": "certification",
    "achievements": "achievement",
}

SOURCE_STRENGTH: dict[EvidenceSource, float] = {
    "experience": 1.0,
    "project": 0.95,
    "certification": 0.72,
    "achievement": 0.62,
    "skills": 0.48,
    "candidate_context": 0.38,
    "other": 0.42,
    "missing": 0,
}


def build_requirement_matches(request: AnalyzeRequest, limit: int = 12) -> list[RequirementMatch]:
    requirements = _extract_requirements(request.jobDescriptionText)
    evidence = _extract_resume_evidence(request.resumeText, request.candidateContext.currentStack)
    matches = [_match_requirement(requirement, evidence) for requirement in requirements[:limit]]
    return matches


def _extract_requirements(jd_text: str) -> list[AtomicRequirement]:
    requirements = []
    sentences = _sentences(jd_text)
    for concept, config in CONCEPTS.items():
        aliases = list(config["aliases"])
        category = str(config["category"])
        semantic_anchor = _semantic_anchor(concept, aliases)
        matching_sentence = _first_matching_text(sentences, aliases) or _first_semantic_text(sentences, semantic_anchor)
        if not matching_sentence:
            continue
        importance = _importance(matching_sentence)
        requirements.append(
            AtomicRequirement(
                text=concept if concept.lower() in matching_sentence.lower() else f"{concept}: {matching_sentence}",
                category=category,
                importance=importance,
                aliases=aliases,
                semanticAnchor=semantic_anchor,
            )
        )
    return _dedupe_requirements(requirements)


def _extract_resume_evidence(resume_text: str, current_stack: list[str]) -> list[ResumeEvidence]:
    evidence = []
    current_section = "other"
    for raw_line in resume_text.splitlines():
        line = re.sub(r"\s+", " ", raw_line).strip(" -")
        if not line:
            continue
        section = _section_for_line(line)
        if section:
            current_section = section
            continue
        source = SECTION_TO_SOURCE.get(current_section, "other")
        for evidence_text in _evidence_units(line):
            categories = _categories_for_text(evidence_text)
            evidence.append(
                ResumeEvidence(
                    text=evidence_text,
                    source=source,
                    categories=categories,
                    strength=SOURCE_STRENGTH[source],
                )
            )

    if current_stack:
        stack_line = "Candidate context stack: " + ", ".join(current_stack)
        evidence.append(
            ResumeEvidence(
                text=stack_line,
                source="candidate_context",
                categories=_categories_for_text(stack_line),
                strength=SOURCE_STRENGTH["candidate_context"],
            )
        )
    return evidence


def _match_requirement(requirement: AtomicRequirement, evidence_items: list[ResumeEvidence]) -> RequirementMatch:
    scored = [(_score_evidence(requirement, evidence), evidence) for evidence in evidence_items]
    if not scored:
        return _missing_match(requirement, "No resume evidence was available.")

    (score, match_type, reason), evidence = max(scored, key=lambda item: item[0][0])
    if score <= 15:
        return _missing_match(requirement, "No meaningful resume evidence matched this JD requirement.")
    return RequirementMatch(
        requirement=requirement.text,
        category=requirement.category,
        importance=requirement.importance,
        bestEvidence=evidence.text,
        evidenceSource=evidence.source,
        score=score,
        matchType=match_type,
        reason=reason,
    )


def _score_evidence(requirement: AtomicRequirement, evidence: ResumeEvidence) -> tuple[int, str, str]:
    text = evidence.text.lower()
    alias_hits = sum(1 for alias in requirement.aliases if _contains(text, alias))
    category_match = requirement.category in evidence.categories
    semantic_hits = _semantic_hits(requirement.category, text)
    embedding_similarity = max(
        cosine_similarity(requirement.semanticAnchor, evidence.text),
        cosine_similarity(requirement.text, evidence.text),
    )

    base = 0
    match_type = "missing"
    if alias_hits >= 2:
        base = 92
        match_type = "strong_alias_match"
    elif alias_hits == 1:
        base = 82
        match_type = "alias_match"
    elif category_match and semantic_hits >= 2:
        base = 76
        match_type = "semantic_category_match"
    elif category_match:
        base = 62
        match_type = "category_match"
    elif embedding_similarity >= 0.22:
        base = round(58 + min((embedding_similarity - 0.22) * 100, 22))
        match_type = "embedding_semantic_match"
    elif semantic_hits:
        base = 46
        match_type = "weak_semantic_signal"

    score = round(base * evidence.strength)
    if evidence.source in {"experience", "project"} and score >= 55:
        reason = "Direct project/experience evidence supports this requirement."
    elif evidence.source == "skills" and score >= 35:
        reason = "The skill is listed, but project or experience proof would be stronger."
    elif evidence.source == "certification" and score >= 35:
        reason = "Certification evidence is relevant, but hands-on project proof may still be needed."
    elif evidence.source == "candidate_context" and score >= 25:
        reason = "The candidate context mentions this area, but the resume should show stronger evidence."
    else:
        reason = "Evidence is weak or indirect for this JD requirement."
    if match_type == "embedding_semantic_match":
        reason = "Embedding similarity found meaningful phrasing overlap even without exact keyword matching."
    return max(0, min(score, 100)), match_type, reason


def _missing_match(requirement: AtomicRequirement, reason: str) -> RequirementMatch:
    return RequirementMatch(
        requirement=requirement.text,
        category=requirement.category,
        importance=requirement.importance,
        bestEvidence=None,
        evidenceSource="missing",
        score=0,
        matchType="missing",
        reason=reason,
    )


def _importance(text: str) -> Literal["high", "medium", "low"]:
    lowered = text.lower()
    if any(token in lowered for token in ["must", "required", "strong", "mandatory", "hands-on"]):
        return "high"
    if any(token in lowered for token in ["preferred", "good to have", "nice to have"]):
        return "low"
    return "medium"


def _section_for_line(line: str) -> str | None:
    normalized = re.sub(r"[^a-z0-9 ]+", " ", line.lower()).strip()
    normalized = re.sub(r"\s+", " ", normalized)
    if normalized in {"experience", "work experience", "professional experience"}:
        return "experience"
    if normalized in {"projects", "personal projects", "academic projects"}:
        return "projects"
    if normalized in {"skills", "technical skills"}:
        return "skills"
    if normalized in {"certifications", "certification", "certificates", "courses", "licenses"}:
        return "certifications"
    if normalized in {"achievements", "online coding platform"}:
        return "achievements"
    return None


def _categories_for_text(text: str) -> set[str]:
    lowered = text.lower()
    categories = set()
    for config in CONCEPTS.values():
        aliases = list(config["aliases"])
        if any(_contains(lowered, alias) for alias in aliases):
            categories.add(str(config["category"]))
    return categories


def _semantic_hits(category: str, text: str) -> int:
    category_terms = {
        "backend": ["endpoint", "controller", "service", "api", "business logic", "integration"],
        "database": ["query", "table", "index", "data", "schema", "performance"],
        "frontend": ["screen", "form", "validation", "ui", "client", "component"],
        "cloud_devops": ["deploy", "deployment", "environment", "pipeline", "release", "cloud", "devops"],
        "security": ["token", "role", "permission", "secure", "login"],
        "debugging_reliability": ["issue", "issues", "bug", "logs", "trace", "traces", "monitor", "production", "live", "support"],
        "system_design": ["scale", "cache", "queue", "architecture", "pagination", "reliable"],
        "problem_solving": ["problems", "coding", "algorithm", "data structure"],
        "ownership": ["delivered", "owned", "requirement", "feature", "end-to-end"],
    }
    return sum(1 for term in category_terms.get(category, []) if term in text)


def _first_matching_text(sentences: list[str], aliases: list[str]) -> str | None:
    for sentence in sentences:
        lowered = sentence.lower()
        if any(_contains(lowered, alias) for alias in aliases):
            return sentence
    return None


def _first_semantic_text(sentences: list[str], anchor: str) -> str | None:
    best_sentence = None
    best_score = 0.0
    for sentence in sentences:
        score = cosine_similarity(anchor, sentence)
        if score > best_score:
            best_score = score
            best_sentence = sentence
    return best_sentence if best_score >= 0.34 else None


def _semantic_anchor(concept: str, aliases: list[str]) -> str:
    return " ".join([concept, *aliases])


def _sentences(text: str) -> list[str]:
    normalized = re.sub(r"\s+", " ", text).strip()
    return [part.strip() for part in re.split(r"(?:[.!?]\s+|[\n;])", normalized) if part.strip()]


def _evidence_units(text: str) -> list[str]:
    sentences = _sentences(text)
    if len(sentences) <= 1:
        return [text]
    return sentences


def _contains(text: str, phrase: str) -> bool:
    escaped = re.escape(phrase.lower()).replace("\\ ", r"\s+")
    return bool(re.search(rf"(?<![a-z0-9+#]){escaped}(?![a-z0-9+#])", text))


def _dedupe_requirements(requirements: list[AtomicRequirement]) -> list[AtomicRequirement]:
    seen = set()
    result = []
    for requirement in requirements:
        key = (requirement.category, requirement.text.lower())
        if key in seen:
            continue
        seen.add(key)
        result.append(requirement)
    return result
