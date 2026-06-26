import re
from dataclasses import dataclass
from typing import Literal

from app.services.embedding_service import semantic_similarity


CertificateLevel = Literal["foundation", "associate", "professional", "specialty", "any"]

CERTIFICATE_SIGNALS = [
    "certified",
    "certification",
    "certificate",
    "credential",
    "badge",
    "exam",
    "license",
    "licensed",
    "course",
]

LEVEL_ALIASES: list[tuple[CertificateLevel, list[str]]] = [
    ("specialty", ["specialty", "specialist"]),
    ("professional", ["professional", "expert", "advanced", "architect"]),
    ("associate", ["associate", "intermediate", "developer", "administrator", "engineer"]),
    ("foundation", ["foundation", "fundamentals", "basic", "basics", "beginner", "practitioner", "entry level"]),
]


@dataclass(frozen=True)
class CertificateEvidence:
    raw_text: str
    provider: str | None
    domain: str
    level: CertificateLevel
    confidence: float


@dataclass(frozen=True)
class CertificationRequirement:
    raw_text: str
    provider: str | None
    domain: str
    level: CertificateLevel
    requires_certification: bool


@dataclass(frozen=True)
class CertificateMatchResult:
    requirement: CertificationRequirement
    best_evidence: CertificateEvidence | None
    score: int
    match_type: str
    reason: str


def extract_certificate_evidence(text: str) -> list[CertificateEvidence]:
    evidence = []
    for line in _candidate_units(text):
        if not _looks_like_certificate(line):
            continue
        evidence.append(
            CertificateEvidence(
                raw_text=line,
                provider=_infer_provider_phrase(line),
                domain=_infer_domain_phrase(line),
                level=_infer_level(line, default="any"),
                confidence=_confidence(line),
            )
        )
    return _dedupe_evidence(evidence)


def extract_certification_requirements(text: str) -> list[CertificationRequirement]:
    requirements = []
    for unit in _candidate_units(text):
        lowered = unit.lower()
        requires_certification = any(signal in lowered for signal in CERTIFICATE_SIGNALS)
        learning_or_basics = any(term in lowered for term in ["fundamental", "basic", "beginner", "awareness", "knowledge"])
        if not (requires_certification or learning_or_basics and _certificate_context(unit)):
            continue
        requirements.append(
            CertificationRequirement(
                raw_text=_clean_requirement(unit),
                provider=_infer_provider_phrase(unit),
                domain=_infer_domain_phrase(unit),
                level=_infer_level(unit, default="any" if requires_certification else "foundation"),
                requires_certification=requires_certification,
            )
        )
    return _dedupe_requirements(requirements)


def best_certificate_match(resume_text: str, jd_text: str) -> CertificateMatchResult | None:
    requirements = extract_certification_requirements(jd_text)
    if not requirements:
        return None
    evidence = extract_certificate_evidence(resume_text)
    best: CertificateMatchResult | None = None
    for requirement in requirements:
        result = _match_requirement(requirement, evidence)
        if best is None or result.score > best.score:
            best = result
    return best


def _match_requirement(requirement: CertificationRequirement, evidence: list[CertificateEvidence]) -> CertificateMatchResult:
    if not evidence:
        return CertificateMatchResult(
            requirement=requirement,
            best_evidence=None,
            score=0 if requirement.requires_certification else 20,
            match_type="no_certificate_evidence",
            reason=f"JD asks for {requirement.raw_text}, but no certificate evidence was found in the resume.",
        )
    scored = [(_score_pair(requirement, item), item) for item in evidence]
    (score, match_type, reason), best_evidence = max(scored, key=lambda item: item[0][0])
    return CertificateMatchResult(
        requirement=requirement,
        best_evidence=best_evidence,
        score=score,
        match_type=match_type,
        reason=reason,
    )


def _score_pair(requirement: CertificationRequirement, evidence: CertificateEvidence) -> tuple[int, str, str]:
    similarity = semantic_similarity(requirement.raw_text, evidence.raw_text)
    overlap = _token_overlap(requirement.raw_text, evidence.raw_text)
    level_fit = _level_fit(requirement.level, evidence.level)
    provider_overlap = bool(requirement.provider and evidence.provider and requirement.provider.lower() in evidence.raw_text.lower())

    base = 0
    match_type = "weak_certificate_relation"
    if similarity.score >= 0.78 or overlap >= 0.7:
        base = 90
        match_type = "semantic_certificate_match"
    elif similarity.score >= 0.62 or overlap >= 0.45:
        base = 75
        match_type = "partial_semantic_certificate_match"
    elif provider_overlap:
        base = 55
        match_type = "provider_phrase_match"
    elif not requirement.requires_certification and evidence.confidence >= 0.65:
        base = 45
        match_type = "related_certificate_evidence"

    if level_fit == 0 and requirement.level != "any":
        base = min(base, 58)
        match_type = "lower_level_certificate_match"

    score = round(base * evidence.confidence)
    reason = (
        f"JD asks for {requirement.raw_text}; resume has {evidence.raw_text}. "
        f"Certificate match used dynamic text similarity with {similarity.provider}/{similarity.model}."
    )
    if similarity.fallbackReason:
        reason += f" Fallback reason: {similarity.fallbackReason}"
    return max(0, min(score, 100)), match_type, reason


def _candidate_units(text: str) -> list[str]:
    units = []
    for line in text.replace("\u00a0", " ").splitlines():
        cleaned = re.sub(r"\s+", " ", line).strip(" ,-•\t")
        if cleaned:
            units.extend(_split_units(cleaned))
    if not units:
        units = _split_units(text)
    return [unit for unit in units if unit]


def _split_units(text: str) -> list[str]:
    pieces = []
    for sentence in re.split(r"(?:[.!?]\s+|[\n;])", text):
        pieces.extend(re.split(r"\s*,\s+|\s+\|\s+", sentence))
    return [piece.strip(" .:-•\t") for piece in pieces if piece.strip(" .:-•\t")]


def _looks_like_certificate(text: str) -> bool:
    lowered = text.lower()
    if any(signal in lowered for signal in CERTIFICATE_SIGNALS):
        return True
    if re.search(r"\b[a-z]{1,4}[-_ ]?\d{2,4}\b", lowered):
        return True
    return _infer_level(text, default="any") != "any" and _certificate_context(text)


def _certificate_context(text: str) -> bool:
    lowered = text.lower()
    return any(term in lowered for term in ["cloud", "security", "data", "ai", "ml", "devops", "project", "agile", "platform", "engineer", "architect"])


def _infer_provider_phrase(text: str) -> str | None:
    code_match = re.search(r"\b([a-z]{1,4})[-_ ]?\d{2,4}\b", text, flags=re.IGNORECASE)
    if code_match:
        return code_match.group(1).upper()
    cert_match = re.search(r"\b([A-Z][A-Za-z0-9&.+-]{1,}(?:\s+[A-Z][A-Za-z0-9&.+-]{1,}){0,2})\s+(?:certified|certification|certificate|credential|exam)", text)
    if cert_match:
        return cert_match.group(1).strip()
    return None


def _infer_domain_phrase(text: str) -> str:
    cleaned = _clean_requirement(text)
    tokens = [
        token
        for token in re.findall(r"[a-zA-Z0-9][a-zA-Z0-9+#.\-]{1,}", cleaned)
        if token.lower() not in {"certified", "certification", "certificate", "credential", "exam", "required", "preferred"}
    ]
    return " ".join(tokens[:6]) if tokens else "general"


def _infer_level(text: str, default: CertificateLevel) -> CertificateLevel:
    lowered = text.lower()
    for level, aliases in LEVEL_ALIASES:
        if any(alias in lowered for alias in aliases):
            return level
    return default


def _level_fit(required: CertificateLevel, actual: CertificateLevel) -> int:
    if required == "any" or actual == "any":
        return 1
    order = {"foundation": 1, "associate": 2, "professional": 3, "specialty": 3}
    return 1 if order.get(actual, 0) >= order.get(required, 0) else 0


def _token_overlap(left: str, right: str) -> float:
    left_tokens = set(_tokens(left))
    right_tokens = set(_tokens(right))
    if not left_tokens:
        return 0
    return len(left_tokens & right_tokens) / len(left_tokens)


def _tokens(text: str) -> list[str]:
    return [
        token
        for token in re.findall(r"[a-zA-Z0-9][a-zA-Z0-9+#.\-]{1,}", text.lower())
        if token not in {"the", "and", "for", "with", "certification", "certificate", "certified", "required", "preferred"}
    ]


def _clean_requirement(text: str) -> str:
    return re.sub(
        r"^(required|mandatory|preferred|good to have|nice to have|must have|should have)\s*[:\-]?\s*",
        "",
        re.sub(r"\s+", " ", text).strip(" .:-"),
        flags=re.IGNORECASE,
    )


def _confidence(text: str) -> float:
    score = 0.55
    lowered = text.lower()
    if any(signal in lowered for signal in CERTIFICATE_SIGNALS):
        score += 0.2
    if re.search(r"\b[a-z]{1,4}[-_ ]?\d{2,4}\b", lowered):
        score += 0.15
    if _infer_level(text, default="any") != "any":
        score += 0.1
    return min(score, 0.98)


def _dedupe_evidence(items: list[CertificateEvidence]) -> list[CertificateEvidence]:
    seen = set()
    result = []
    for item in items:
        key = item.raw_text.lower()
        if key in seen:
            continue
        seen.add(key)
        result.append(item)
    return result


def _dedupe_requirements(items: list[CertificationRequirement]) -> list[CertificationRequirement]:
    seen = set()
    result = []
    for item in items:
        key = item.raw_text.lower()
        if key in seen:
            continue
        seen.add(key)
        result.append(item)
    return result
