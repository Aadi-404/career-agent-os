import re
from dataclasses import dataclass
from typing import Literal

from app.models.analysis import AnalyzeRequest, RequirementMatch
from app.services.embedding_service import SimilarityResult, semantic_similarity


EvidenceSource = Literal["experience", "project", "skills", "certification", "achievement", "candidate_context", "other", "missing"]
Importance = Literal["high", "medium", "low"]

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
    "certification": 0.74,
    "achievement": 0.64,
    "skills": 0.56,
    "candidate_context": 0.42,
    "other": 0.44,
    "missing": 0,
}

REQUIREMENT_SECTION_HEADERS = {
    "required skills",
    "requirements",
    "must have",
    "mandatory skills",
    "technical skills",
    "qualifications",
    "responsibilities",
    "what you will do",
    "role and responsibilities",
    "preferred skills",
    "good to have",
    "nice to have",
}

STOPWORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "be",
    "by",
    "for",
    "from",
    "have",
    "in",
    "is",
    "it",
    "of",
    "on",
    "or",
    "our",
    "the",
    "this",
    "to",
    "with",
    "you",
    "your",
}


@dataclass(frozen=True)
class AtomicRequirement:
    text: str
    category: str
    importance: Importance
    aliases: list[str]
    semanticAnchor: str
    sourceText: str


@dataclass(frozen=True)
class ResumeEvidence:
    text: str
    source: EvidenceSource
    strength: float


def build_requirement_matches(request: AnalyzeRequest, limit: int = 12) -> list[RequirementMatch]:
    requirements = _extract_requirements(request.jobDescriptionText, limit=limit)
    evidence = _extract_resume_evidence(request.resumeText, request.candidateContext.currentStack)
    return [_match_requirement(requirement, evidence) for requirement in requirements]


def _extract_requirements(jd_text: str, limit: int) -> list[AtomicRequirement]:
    candidates: list[AtomicRequirement] = []
    active_section = ""

    for line in _clean_lines(jd_text):
        section = _section_header(line)
        if section:
            active_section = section
            line = _strip_section_prefix(line)
            if not line:
                continue

        for unit in _requirement_units(line):
            cleaned = _clean_requirement(unit)
            if not _looks_like_requirement(cleaned, active_section):
                continue
            category = _category_for_requirement(cleaned, active_section)
            candidates.append(
                AtomicRequirement(
                    text=cleaned,
                    category=category,
                    importance=_importance(cleaned, active_section),
                    aliases=_aliases_for_requirement(cleaned),
                    semanticAnchor=_semantic_anchor(cleaned, category, active_section),
                    sourceText=line,
                )
            )

    return _dedupe_requirements(candidates)[:limit]


def _extract_resume_evidence(resume_text: str, current_stack: list[str]) -> list[ResumeEvidence]:
    evidence = []
    current_section = "other"

    for raw_line in resume_text.splitlines():
        line = re.sub(r"\s+", " ", raw_line).strip(" -•\t")
        if not line:
            continue
        section = _resume_section_for_line(line)
        if section:
            current_section = section
            continue

        source = SECTION_TO_SOURCE.get(current_section, "other")
        for evidence_text in _evidence_units(line):
            evidence.append(
                ResumeEvidence(
                    text=evidence_text,
                    source=source,
                    strength=SOURCE_STRENGTH[source],
                )
            )

    if current_stack:
        evidence.append(
            ResumeEvidence(
                text="Candidate context stack: " + ", ".join(current_stack),
                source="candidate_context",
                strength=SOURCE_STRENGTH["candidate_context"],
            )
        )
    return evidence


def _match_requirement(requirement: AtomicRequirement, evidence_items: list[ResumeEvidence]) -> RequirementMatch:
    scored = [(_score_evidence(requirement, evidence), evidence) for evidence in evidence_items]
    if not scored:
        return _missing_match(requirement, "No resume evidence was available.")

    (score, match_type, reason), evidence = max(scored, key=lambda item: item[0][0])
    if score <= 18:
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
    alias_hits = _alias_hits(requirement.aliases, evidence.text)
    token_overlap = _token_overlap(requirement.text, evidence.text)
    similarity = semantic_similarity(requirement.semanticAnchor, evidence.text)

    base = 0
    match_type = "missing"
    if alias_hits >= 2 or token_overlap >= 0.72:
        base = 92
        match_type = "strong_dynamic_phrase_match"
    elif alias_hits == 1 or token_overlap >= 0.48:
        base = 78
        match_type = "dynamic_phrase_match"
    elif similarity.score >= 0.78:
        base = 86
        match_type = "strong_embedding_semantic_match"
    elif similarity.score >= 0.62:
        base = 74
        match_type = "embedding_semantic_match"
    elif similarity.score >= 0.48:
        base = 58
        match_type = "weak_embedding_semantic_match"

    score = round(base * evidence.strength)
    return max(0, min(score, 100)), match_type, _reason(match_type, evidence, similarity)


def _reason(match_type: str, evidence: ResumeEvidence, similarity: SimilarityResult) -> str:
    if match_type in {"strong_dynamic_phrase_match", "dynamic_phrase_match"}:
        return "Resume evidence repeats or closely overlaps the JD requirement wording."
    if "embedding" in match_type:
        provider_label = f"{similarity.provider}/{similarity.model}"
        reason = (
            "Embedding similarity matched the JD requirement to resume evidence by meaning, "
            f"using {provider_label}."
        )
        if not similarity.live and similarity.fallbackReason:
            reason += f" Fallback reason: {similarity.fallbackReason}"
        return reason
    if evidence.source == "skills":
        return "The evidence is only listed as a skill; project or experience proof would be stronger."
    return "Evidence is weak or indirect for this JD requirement."


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


def _clean_lines(text: str) -> list[str]:
    lines = []
    for raw_line in text.replace("\u00a0", " ").splitlines():
        line = re.sub(r"\s+", " ", raw_line).strip(" -•\t")
        if line:
            lines.append(line)
    if lines:
        return lines
    compact = re.sub(r"\s+", " ", text).strip()
    return [compact] if compact else []


def _section_header(line: str) -> str | None:
    normalized = re.sub(r"[^a-z0-9 ]+", " ", line.lower()).strip()
    normalized = re.sub(r"\s+", " ", normalized)
    for header in REQUIREMENT_SECTION_HEADERS:
        if normalized == header or normalized.startswith(f"{header} "):
            return header
    return None


def _strip_section_prefix(line: str) -> str:
    return re.sub(
        r"^\s*(required skills|requirements|must have|mandatory skills|technical skills|qualifications|responsibilities|what you will do|role and responsibilities|preferred skills|good to have|nice to have)\s*[:\-]?\s*",
        "",
        line,
        flags=re.IGNORECASE,
    ).strip()


def _requirement_units(line: str) -> list[str]:
    units = []
    for sentence in _sentences(line):
        parts = re.split(r"\s*[;,]\s+|\s+\|\s+|\s+/\s+(?=[A-Z0-9])", sentence)
        units.extend(part for part in parts if part.strip())
    return units


def _clean_requirement(text: str) -> str:
    text = re.sub(r"^(?:\(?\d+\)\s*|\d+\.\s+)", "", text)
    text = re.sub(r"^[•*-]\s*", "", text)
    text = re.sub(r"\s+", " ", text).strip(" .:-")
    text = re.sub(
        r"^(candidate should|you should|must have|should have|required|mandatory|responsibilities|responsibility|experience with|knowledge of|strong knowledge of|hands-on experience with)\s*[:\-]?\s+",
        "",
        text,
        flags=re.IGNORECASE,
    )
    return text.strip(" .:-")


def _looks_like_requirement(text: str, active_section: str) -> bool:
    if len(text) < 2 or len(text) > 180:
        return False
    lowered = text.lower()
    if re.search(r"\b\d+(?:\.\d+)?\s*(?:to|-|\+)?\s*\d*(?:\.\d+)?\s*(?:years?|yrs?)\b", lowered):
        return False
    if any(label in lowered for label in ["work mode", "working mode", "location:", "job location", "office location"]):
        return False
    if active_section:
        return True
    if _token_count(text) == 1:
        return _has_technical_shape(text)
    requirement_signals = [
        "experience",
        "knowledge",
        "skill",
        "proficient",
        "familiar",
        "understand",
        "build",
        "develop",
        "design",
        "implement",
        "manage",
        "deploy",
        "debug",
        "test",
        "integrate",
        "certification",
        "degree",
    ]
    return bool(active_section or _has_technical_shape(text) or any(signal in lowered for signal in requirement_signals))


def _category_for_requirement(text: str, active_section: str) -> str:
    lowered = f"{active_section} {text}".lower()
    if any(term in lowered for term in ["certification", "certified", "certificate"]):
        return "certification"
    if any(term in lowered for term in ["responsibilities", "build", "develop", "design", "implement", "maintain", "debug", "deliver"]):
        return "responsibility"
    if any(term in lowered for term in ["years", "experience"]):
        return "experience"
    if any(term in lowered for term in ["degree", "qualification", "education"]):
        return "qualification"
    if any(term in lowered for term in ["preferred", "good to have", "nice to have"]):
        return "preferred_requirement"
    return "technical_requirement"


def _importance(text: str, active_section: str) -> Importance:
    lowered = f"{active_section} {text}".lower()
    if any(token in lowered for token in ["preferred", "good to have", "nice to have"]):
        return "low"
    high_markers = [
        "must",
        "required",
        "mandatory",
        "strong",
        "hands-on",
        "deep",
        "advanced",
        "expertise",
        "proven",
        "solid",
        "critical",
        "core",
        "primary",
        "essential",
        "requirements",
        "technical skills",
    ]
    if any(token in lowered for token in high_markers):
        return "high"
    return "medium"


def _aliases_for_requirement(text: str) -> list[str]:
    aliases = [text]
    tokens = _meaningful_tokens(text)
    aliases.extend(tokens)
    aliases.extend(" ".join(tokens[index : index + 2]) for index in range(max(0, len(tokens) - 1)))
    return _unique(alias for alias in aliases if len(alias) >= 2)


def _semantic_anchor(text: str, category: str, active_section: str) -> str:
    context = " ".join(part for part in [active_section, category, text] if part)
    return context.strip()


def _resume_section_for_line(line: str) -> str | None:
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


def _evidence_units(text: str) -> list[str]:
    sentences = _sentences(text)
    return sentences if len(sentences) > 1 else [text]


def _sentences(text: str) -> list[str]:
    normalized = re.sub(r"\s+", " ", text).strip()
    return [part.strip() for part in re.split(r"(?:[!?]\s+|(?<!\d)\.\s+|[\n])", normalized) if part.strip()]


def _alias_hits(aliases: list[str], text: str) -> int:
    lowered = text.lower()
    return sum(1 for alias in aliases if _contains_phrase(lowered, alias.lower()))


def _token_overlap(left: str, right: str) -> float:
    left_tokens = set(_meaningful_tokens(left))
    right_tokens = set(_meaningful_tokens(right))
    if not left_tokens:
        return 0
    return len(left_tokens & right_tokens) / len(left_tokens)


def _meaningful_tokens(text: str) -> list[str]:
    tokens = re.findall(r"[a-zA-Z0-9][a-zA-Z0-9+#.\-]{1,}", text.lower())
    return [token for token in tokens if token not in STOPWORDS]


def _token_count(text: str) -> int:
    return len(re.findall(r"[a-zA-Z0-9][a-zA-Z0-9+#.\-]*", text))


def _has_technical_shape(text: str) -> bool:
    return bool(
        re.search(r"[A-Z]{2,}|\w+[+#.]|\d|[-/]", text)
        or re.search(r"\b(api|sdk|framework|database|cloud|pipeline|model|server|frontend|backend|testing)\b", text, flags=re.IGNORECASE)
    )


def _contains_phrase(text: str, phrase: str) -> bool:
    escaped = re.escape(phrase).replace("\\ ", r"\s+")
    return bool(re.search(rf"(?<![a-z0-9+#.\-]){escaped}(?![a-z0-9+#.\-])", text))


def _unique(values: list[str] | tuple[str, ...] | set[str] | object) -> list[str]:
    seen = set()
    result = []
    for value in values:
        key = str(value).lower()
        if key in seen:
            continue
        seen.add(key)
        result.append(str(value))
    return result


def _dedupe_requirements(requirements: list[AtomicRequirement]) -> list[AtomicRequirement]:
    seen = set()
    result = []
    for requirement in requirements:
        key = " ".join(_meaningful_tokens(requirement.text))
        if not key or key in seen:
            continue
        seen.add(key)
        result.append(requirement)
    return result
