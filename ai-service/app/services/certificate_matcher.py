import re
from dataclasses import dataclass
from typing import Literal


CertificateLevel = Literal["foundation", "associate", "professional", "specialty", "any"]


@dataclass
class CertificateEvidence:
    raw_text: str
    provider: str | None
    domain: str
    level: CertificateLevel
    confidence: float


@dataclass
class CertificationRequirement:
    raw_text: str
    provider: str | None
    domain: str
    level: CertificateLevel
    requires_certification: bool


@dataclass
class CertificateMatchResult:
    requirement: CertificationRequirement
    best_evidence: CertificateEvidence | None
    score: int
    match_type: str
    reason: str


PROVIDER_ALIASES = {
    "azure": ["azure", "microsoft"],
    "aws": ["aws", "amazon web services"],
    "gcp": ["gcp", "google cloud"],
    "oracle": ["oracle"],
    "salesforce": ["salesforce"],
    "kubernetes": ["kubernetes", "cka", "ckad"],
    "docker": ["docker"],
    "scrum": ["scrum", "agile"],
}

DOMAIN_ALIASES = {
    "cloud": ["cloud", "azure", "aws", "gcp", "google cloud", "cloud practitioner", "digital leader"],
    "cloud_architecture": ["architect", "architecture", "solutions architect", "cloud architect"],
    "devops": ["devops", "ci/cd", "pipeline", "deployment", "kubernetes", "docker"],
    "security": ["security", "cyber", "iam", "identity"],
    "database": ["database", "sql", "dbms", "oracle", "postgres", "mysql"],
    "ai_ml": ["ai", "machine learning", "ml", "data science", "tensorflow"],
    "backend": ["java", ".net", "spring", "api", "backend"],
    "frontend": ["frontend", "react", "angular", "javascript"],
    "project_management": ["scrum", "agile", "pmp", "project management"],
}

LEVEL_ALIASES: list[tuple[CertificateLevel, list[str]]] = [
    ("specialty", ["specialty", "specialist"]),
    ("professional", ["professional", "expert", "advanced", "architect"]),
    ("associate", ["associate", "intermediate", "developer", "administrator", "engineer"]),
    ("foundation", ["foundation", "fundamentals", "basic", "basics", "beginner", "practitioner", "digital leader"]),
]

CERTIFICATE_SIGNALS = [
    "certified",
    "certification",
    "certificate",
    "credential",
    "badge",
    "exam",
    "course",
    "fundamentals",
    "practitioner",
    "associate",
    "professional",
    "specialty",
    "digital leader",
]


def extract_certificate_evidence(text: str) -> list[CertificateEvidence]:
    evidence = []
    for line in _candidate_lines(text):
        if not _looks_like_certificate(line):
            continue
        provider = _infer_provider(line)
        domain = _infer_domain(line)
        level = _infer_level(line, default="foundation")
        confidence = _confidence(line, provider, level)
        evidence.append(
            CertificateEvidence(
                raw_text=line,
                provider=provider,
                domain=domain,
                level=level,
                confidence=confidence,
            )
        )
    return _dedupe_evidence(evidence)


def extract_certification_requirements(text: str) -> list[CertificationRequirement]:
    requirements = []
    for sentence in _sentences(text):
        lowered = sentence.lower()
        has_cloud_intent = any(term in lowered for term in ["cloud basic", "cloud basics", "cloud knowledge", "cloud fundamentals"])
        has_cert_intent = any(signal in lowered for signal in ["certification", "certified", "certificate", "credential"])
        has_provider_cert = _infer_provider(sentence) is not None and any(signal in lowered for signal in CERTIFICATE_SIGNALS)
        if not (has_cloud_intent or has_cert_intent or has_provider_cert):
            continue

        requirements.append(
            CertificationRequirement(
                raw_text=sentence,
                provider=_infer_provider(sentence),
                domain=_infer_domain(sentence),
                level=_infer_level(sentence, default="any" if has_cert_intent and not has_cloud_intent else "foundation"),
                requires_certification=has_cert_intent or has_provider_cert,
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
            score=20 if not requirement.requires_certification else 0,
            match_type="no_certificate_evidence",
            reason=f"JD asks for {requirement.domain} {requirement.level} certification/knowledge, but no certificate evidence was found in the resume.",
        )

    scored = [(_score_pair(requirement, item), item) for item in evidence]
    score, best_evidence = max(scored, key=lambda item: item[0][0])
    match_score, match_type, reason = score
    return CertificateMatchResult(
        requirement=requirement,
        best_evidence=best_evidence,
        score=match_score,
        match_type=match_type,
        reason=reason,
    )


def _score_pair(requirement: CertificationRequirement, evidence: CertificateEvidence) -> tuple[int, str, str]:
    provider_match = requirement.provider is None or requirement.provider == evidence.provider
    same_domain = requirement.domain == evidence.domain or _compatible_domain(requirement.domain, evidence.domain)
    level_fit = _level_fit(requirement.level, evidence.level)

    if provider_match and same_domain and level_fit >= 1:
        return (
            95 if requirement.provider else 88,
            "provider_domain_level_match" if requirement.provider else "domain_level_match",
            f"JD asks for {requirement.raw_text}; resume has {evidence.raw_text}, which matches the expected domain and level.",
        )
    if same_domain and level_fit >= 1:
        return (
            75,
            "same_domain_different_provider",
            f"JD asks for {requirement.raw_text}; resume has {evidence.raw_text}. Domain and level match, but provider differs.",
        )
    if provider_match and same_domain and level_fit == 0:
        return (
            58,
            "same_provider_domain_lower_level",
            f"JD expects a higher level for {requirement.raw_text}; resume has {evidence.raw_text}, which is relevant but lower level.",
        )
    if same_domain:
        return (
            50,
            "same_domain_partial_level",
            f"JD asks for {requirement.raw_text}; resume has {evidence.raw_text}. Domain is related, but level/provider fit is partial.",
        )
    if provider_match:
        return (
            42,
            "same_provider_different_domain",
            f"JD asks for {requirement.raw_text}; resume has {evidence.raw_text}. Provider matches, but certification domain is different.",
        )
    return (
        25,
        "weak_certificate_relation",
        f"JD asks for {requirement.raw_text}; resume has {evidence.raw_text}, but the domain/provider/level relation is weak.",
    )


def _candidate_lines(text: str) -> list[str]:
    lines = []
    for raw_line in text.splitlines():
        line = re.sub(r"\s+", " ", raw_line).strip(" ,-")
        if line:
            lines.append(line)
    if len(lines) <= 1:
        lines = _sentences(text)
    return lines


def _looks_like_certificate(text: str) -> bool:
    lowered = text.lower()
    if any(signal in lowered for signal in CERTIFICATE_SIGNALS):
        return True
    if re.search(r"\b(?:az|ai|dp|pl|sc|ms)-\d{3}\b", lowered):
        return True
    return bool(_infer_provider(text) and _infer_level(text, default="any") != "any")


def _infer_provider(text: str) -> str | None:
    lowered = text.lower()
    for provider, aliases in PROVIDER_ALIASES.items():
        if any(alias in lowered for alias in aliases):
            return provider
    return None


def _infer_domain(text: str) -> str:
    lowered = text.lower()
    for domain, aliases in DOMAIN_ALIASES.items():
        if any(alias in lowered for alias in aliases):
            return domain
    return "general"


def _infer_level(text: str, default: CertificateLevel) -> CertificateLevel:
    lowered = text.lower()
    for level, aliases in LEVEL_ALIASES:
        if any(alias in lowered for alias in aliases):
            return level
    return default


def _level_fit(required: CertificateLevel, actual: CertificateLevel) -> int:
    if required == "any":
        return 1
    order = {"foundation": 1, "associate": 2, "professional": 3, "specialty": 3}
    return 1 if order.get(actual, 0) >= order.get(required, 0) else 0


def _compatible_domain(required: str, actual: str) -> bool:
    if required == "cloud" and actual in {"cloud_architecture", "devops", "security"}:
        return True
    if required == "cloud_architecture" and actual == "cloud":
        return True
    return False


def _confidence(text: str, provider: str | None, level: CertificateLevel) -> float:
    score = 0.55
    if provider:
        score += 0.2
    if level != "any":
        score += 0.15
    if any(signal in text.lower() for signal in ["certified", "certification", "certificate", "credential"]):
        score += 0.1
    return min(score, 0.98)


def _sentences(text: str) -> list[str]:
    return [part.strip() for part in re.split(r"(?:[.!?]\s+|[\n;])", text) if part.strip()]


def _dedupe_evidence(items: list[CertificateEvidence]) -> list[CertificateEvidence]:
    seen = set()
    result = []
    for item in items:
        key = item.raw_text.lower()
        if key not in seen:
            seen.add(key)
            result.append(item)
    return result


def _dedupe_requirements(items: list[CertificationRequirement]) -> list[CertificationRequirement]:
    seen = set()
    result = []
    for item in items:
        key = (item.provider, item.domain, item.level, item.raw_text.lower())
        if key not in seen:
            seen.add(key)
            result.append(item)
    return result
