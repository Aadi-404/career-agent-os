import re
import json

from app.core.config import get_settings
from app.models.jd_parse import ExperienceRange, JdParseRequest, JdParseResponse, ParsedJobDescription
from app.services.certificate_matcher import extract_certification_requirements
from app.services.llm_client import call_llm


SKILL_STOPWORDS = {
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
    "of",
    "on",
    "or",
    "the",
    "to",
    "with",
    "you",
    "your",
}

def parse_jd(request: JdParseRequest) -> JdParseResponse:
    settings = get_settings()
    if settings.jd_parser_mode in {"llm", "auto"} and settings.llm_mode == "live":
        llm_response = _parse_jd_with_llm(request, settings)
        if llm_response or settings.jd_parser_mode == "llm":
            return llm_response or _parse_jd_deterministic(request)
    return _parse_jd_deterministic(request)


def _parse_jd_deterministic(request: JdParseRequest) -> JdParseResponse:
    lines = _clean_lines(request.rawJobDescriptionText)
    text = "\n".join(lines)
    parsed = ParsedJobDescription(
        roleTitle=_extract_role_title(lines),
        experienceRange=_extract_experience_range(text),
        requiredSkills=_extract_required_skills(text),
        preferredSkills=_extract_preferred_skills(text),
        requiredCertifications=_extract_required_certifications(text),
        emphasizedRequirements=_extract_emphasized_requirements(text),
        responsibilities=_extract_responsibilities(lines),
        locations=_extract_locations(text),
        workModes=_extract_work_modes(text),
        senioritySignals=_extract_seniority_signals(text),
    )
    return JdParseResponse(
        normalizedJobDescriptionText=_format_normalized_jd(parsed, lines),
        parsedJobDescription=parsed,
        warnings=_build_warnings(parsed),
    )


def _parse_jd_with_llm(request: JdParseRequest, settings) -> JdParseResponse | None:
    prompt = f"""
Return only valid JSON matching this schema:
{{
  "roleTitle": string | null,
  "experienceRange": {{"minYears": number | null, "maxYears": number | null}},
  "requiredSkills": string[],
  "preferredSkills": string[],
  "requiredCertifications": string[],
  "emphasizedRequirements": string[],
  "responsibilities": string[],
  "locations": string[],
  "workModes": string[],
  "senioritySignals": string[]
}}

Rules:
- Extract requirements from the JD text itself. Do not use a fixed skill list.
- Preserve technologies, certifications, locations, and work modes as written when possible.
- Put must-have, repeated, strongly worded, or role-critical requirements in emphasizedRequirements.
- Experience years may be decimal, for example 2.5.
- Use empty arrays when fields are absent.

JD:
{request.rawJobDescriptionText}
""".strip()
    try:
        raw = call_llm(prompt, settings, settings.llm_provider, settings.llm_model)
        parsed_json = _parse_json(raw)
        parsed = ParsedJobDescription.model_validate(parsed_json)
    except Exception:
        return None

    normalized = _format_normalized_jd(parsed, _clean_lines(request.rawJobDescriptionText))
    warnings = _build_warnings(parsed)
    if settings.jd_parser_mode == "auto":
        warnings.append("JD was parsed with the configured LLM parser; deterministic parser remains the fallback.")
    return JdParseResponse(normalizedJobDescriptionText=normalized, parsedJobDescription=parsed, warnings=warnings)


def _clean_lines(text: str) -> list[str]:
    lines = []
    for raw_line in text.replace("\u00a0", " ").splitlines():
        line = re.sub(r"\s+", " ", raw_line).strip(" ,.-")
        if line:
            lines.append(line)
    if not lines:
        compact = re.sub(r"\s+", " ", text).strip()
        if compact:
            lines.append(compact)
    return lines


def _parse_json(raw_response: str) -> dict:
    cleaned = raw_response.strip()
    fence_match = re.search(r"```(?:json)?\s*(.*?)```", cleaned, flags=re.DOTALL)
    if fence_match:
        cleaned = fence_match.group(1).strip()
    return json.loads(cleaned)


def _extract_role_title(lines: list[str]) -> str | None:
    title_patterns = [
        r"(?:looking for|hiring|opening for|role[:\s]+|position[:\s]+)\s+(?:an?\s+)?([^.,\n]{3,80})",
        r"([^.,\n]{3,80}\b(?:developer|engineer|architect|lead|analyst|consultant)\b[^.,\n]*)",
    ]
    text = " ".join(lines[:4])
    for pattern in title_patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            return _clean_title(match.group(1))
    return lines[0][:80] if lines else None


def _clean_title(value: str) -> str:
    value = re.split(r"\bwith\b|\brequired\b|\bwho\b", value, flags=re.IGNORECASE)[0]
    return value.strip(" :-")


def _extract_experience_range(text: str) -> ExperienceRange:
    lowered = text.lower()
    range_match = re.search(r"(\d+(?:\.\d+)?)\s*(?:-|to)\s*(\d+(?:\.\d+)?)\s*(?:years?|yrs?)", lowered)
    if range_match:
        return ExperienceRange(minYears=float(range_match.group(1)), maxYears=float(range_match.group(2)))
    min_match = re.search(r"(?:minimum|min|at least)\s*(\d+(?:\.\d+)?)\s*(?:years?|yrs?)", lowered)
    if min_match:
        return ExperienceRange(minYears=float(min_match.group(1)))
    single_match = re.search(r"(\d+(?:\.\d+)?)\+?\s*(?:years?|yrs?)", lowered)
    if single_match:
        return ExperienceRange(minYears=float(single_match.group(1)))
    return ExperienceRange()


def _extract_required_skills(text: str) -> list[str]:
    phrases = _extract_skill_phrases(text, mode="required")
    if phrases:
        return phrases[:12]
    return _extract_skill_phrases(text, mode="all")[:12]


def _extract_preferred_skills(text: str) -> list[str]:
    required = {skill.lower() for skill in _extract_required_skills(text)}
    preferred = [
        skill
        for skill in _extract_skill_phrases(text, mode="preferred")
        if skill.lower() not in required
    ]
    return preferred[:12]


def _extract_required_certifications(text: str) -> list[str]:
    requirements = extract_certification_requirements(text)
    labels = []
    for requirement in requirements:
        provider = requirement.provider.upper() if requirement.provider else "Any provider"
        labels.append(f"{provider} {requirement.domain} {requirement.level}: {requirement.raw_text}")
    return labels


def _extract_emphasized_requirements(text: str) -> list[str]:
    emphasis_tokens = [
        "must have",
        "mandatory",
        "required",
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
        "key responsibility",
        "essential",
    ]
    emphasized = []
    for sentence in _sentences(text):
        lowered = sentence.lower()
        if not any(token in lowered for token in emphasis_tokens):
            continue
        cleaned = re.sub(
            r"^(?:must have|required|mandatory|strong|hands-on|deep|advanced|proven|solid|critical|core|primary|essential|core responsibility is|key responsibility is)\s+",
            "",
            sentence.strip(" .:-"),
            flags=re.IGNORECASE,
        )
        emphasized.append(_sentence(cleaned))

    repeated_candidates = _extract_skill_phrases(text, mode="all")
    lowered_text = text.lower()
    for candidate in repeated_candidates:
        if len(candidate.split()) <= 1:
            continue
        if lowered_text.count(candidate.lower()) >= 2:
            emphasized.append(candidate)

    return _dedupe_preserve_order([item for item in emphasized if 3 <= len(item) <= 140])[:10]


def _extract_skill_phrases(text: str, mode: str) -> list[str]:
    results = []
    for sentence in _sentences(text):
        lowered = sentence.lower()
        is_preferred = any(token in lowered for token in ["preferred", "good to have", "nice to have", "plus"])
        is_required = any(token in lowered for token in ["required", "mandatory", "must have", "should have", "strong", "hands-on", "core", "critical", "essential"])
        if any(token in lowered for token in ["responsibility", "responsibilities", "accountable for"]):
            continue
        if mode == "required" and (is_preferred or not is_required):
            continue
        if mode == "preferred" and not is_preferred:
            continue

        cleaned = re.sub(
            r"^(required skills|skills|required|mandatory|must have|should have|preferred|good to have|nice to have|strong knowledge of|hands-on experience with|core skills|critical requirements|essential skills)\s*[:\-]?\s*",
            "",
            sentence,
            flags=re.IGNORECASE,
        )
        for phrase in re.split(r"\s*[;,]\s+|\s+\|\s+|\s+and/or\s+", cleaned):
            skill = _clean_skill_phrase(phrase)
            if _looks_like_skill_phrase(skill):
                results.append(skill)
    return _dedupe_preserve_order(results)


def _clean_skill_phrase(value: str) -> str:
    value = re.sub(r"^(?:\(?\d+\)\s*|\d+\.\s+)", "", value.strip(" .:-*"))
    value = re.sub(
        r"^(strong hands-on|hands-on|strong|deep|advanced|proven|solid|experience with|knowledge of|proficiency in|familiarity with|understanding of|ability to|work with|using)\s+",
        "",
        value,
        flags=re.IGNORECASE,
    )
    return re.sub(r"\s+", " ", value).strip(" .:-")


def _looks_like_skill_phrase(value: str) -> bool:
    if len(value) < 2 or len(value) > 90:
        return False
    if re.search(r"\b\d+(?:\.\d+)?\s*(?:to|-|\+)?\s*\d*(?:\.\d+)?\s*(?:years?|yrs?)\b", value, flags=re.IGNORECASE):
        return False
    tokens = re.findall(r"[a-zA-Z0-9][a-zA-Z0-9+#.\-]*", value)
    if not tokens:
        return False
    meaningful = [token for token in tokens if token.lower() not in SKILL_STOPWORDS]
    if not meaningful:
        return False
    if len(meaningful) <= 5:
        return True
    return any(re.search(r"[A-Z]{2,}|\d|[+#./-]", token) for token in meaningful)


def _dedupe_preserve_order(values: list[str]) -> list[str]:
    seen = set()
    result = []
    for value in values:
        key = value.lower()
        if key in seen:
            continue
        seen.add(key)
        result.append(value)
    return result


def _sentences(text: str) -> list[str]:
    return [part.strip() for part in re.split(r"(?:[!?]\s+|(?<!\d)\.\s+|[\n;])", text) if part.strip()]


def _extract_responsibilities(lines: list[str]) -> list[str]:
    responsibilities = []
    action_words = (
        "build",
        "building",
        "develop",
        "design",
        "maintain",
        "implement",
        "integrate",
        "optimize",
        "debug",
        "participate",
        "collaborate",
        "work",
        "deliver",
    )
    for line in lines:
        for sentence in _sentences(line):
            lowered = sentence.lower()
            if lowered.startswith(action_words) or any(f" {word} " in f" {lowered} " for word in action_words):
                responsibilities.append(_sentence(sentence))
    return responsibilities[:8]


def _extract_locations(text: str) -> list[str]:
    locations = []
    patterns = [
        r"(?:location|locations|work location|job location|office location)\s*[:\-]\s*([^.\n;]+)",
        r"(?:based in|located in|office in|work from)\s+([^.\n;]+)",
    ]
    for pattern in patterns:
        for match in re.finditer(pattern, text, flags=re.IGNORECASE):
            locations.extend(_split_location_phrase(match.group(1)))
    return _dedupe_preserve_order(locations)


def _extract_work_modes(text: str) -> list[str]:
    found = []
    patterns = [
        r"\b(remote|hybrid|onsite|on-site|work from home|work from office|wfh|wfo|field work|client location)\b",
        r"(?:work mode|working mode|mode of work)\s*[:\-]\s*([^.\n;]+)",
    ]
    for pattern in patterns:
        for match in re.finditer(pattern, text, flags=re.IGNORECASE):
            found.extend(_split_work_mode_phrase(match.group(1)))
    return _dedupe_preserve_order(found)


def _split_location_phrase(value: str) -> list[str]:
    cleaned = re.split(r"\b(?:remote|hybrid|onsite|on-site|work from home|work from office|wfh|wfo)\b", value, flags=re.IGNORECASE)[0]
    parts = re.split(r"\s*,\s*|\s+/\s+|\s+\bor\b\s+|\s+\band\b\s+", cleaned)
    return [_clean_location(part) for part in parts if _clean_location(part)]


def _clean_location(value: str) -> str:
    value = re.sub(r"\b(?:hybrid|remote|onsite|on-site|wfh|wfo)\b", "", value, flags=re.IGNORECASE)
    value = re.sub(r"\s+", " ", value).strip(" .:-")
    if not value or len(value) > 80:
        return ""
    return value.title()


def _split_work_mode_phrase(value: str) -> list[str]:
    parts = re.split(r"\s*,\s*|\s+/\s+|\s+\bor\s+|\s+\band\s+", value)
    return [_normalize_work_mode(part) for part in parts if _normalize_work_mode(part)]


def _normalize_work_mode(value: str) -> str:
    lowered = value.lower().strip(" .:-")
    if lowered in {"wfh", "work from home"}:
        return "remote"
    if lowered in {"wfo", "work from office", "client location", "field work"}:
        return lowered
    if lowered == "on-site":
        return "onsite"
    if lowered in {"remote", "hybrid", "onsite"}:
        return lowered
    return lowered if 2 <= len(lowered) <= 40 else ""


def _extract_seniority_signals(text: str) -> list[str]:
    lowered = text.lower()
    signals = []
    if any(token in lowered for token in ["junior", "fresher", "entry level"]):
        signals.append("junior")
    if any(token in lowered for token in ["senior", "lead", "architect"]):
        signals.append("senior")
    if any(token in lowered for token in ["own", "ownership", "end-to-end", "independently"]):
        signals.append("ownership")
    if any(token in lowered for token in ["mentor", "review", "code review"]):
        signals.append("mentoring")
    return signals


def _sentence(text: str) -> str:
    text = text.strip(" .")
    return f"{text}."


def _format_normalized_jd(parsed: ParsedJobDescription, lines: list[str]) -> str:
    output = []
    if parsed.roleTitle:
        output.extend(["Role", parsed.roleTitle])
    if parsed.experienceRange.minYears is not None:
        max_label = f" - {parsed.experienceRange.maxYears}" if parsed.experienceRange.maxYears is not None else "+"
        output.extend(["", "Experience", f"{parsed.experienceRange.minYears}{max_label} years"])
    if parsed.requiredSkills:
        output.extend(["", "Required Skills", ", ".join(parsed.requiredSkills)])
    if parsed.preferredSkills:
        output.extend(["", "Preferred Skills", ", ".join(parsed.preferredSkills)])
    if parsed.requiredCertifications:
        output.extend(["", "Required Certifications", ", ".join(parsed.requiredCertifications)])
    if parsed.emphasizedRequirements:
        output.extend(["", "Emphasized Requirements"])
        output.extend(f"- {item}" for item in parsed.emphasizedRequirements)
    if parsed.locations or parsed.workModes:
        details = []
        if parsed.locations:
            details.append("Locations: " + ", ".join(parsed.locations))
        if parsed.workModes:
            details.append("Work modes: " + ", ".join(parsed.workModes))
        output.extend(["", "Hiring Context", *details])
    if parsed.responsibilities:
        output.extend(["", "Responsibilities"])
        output.extend(f"- {item}" for item in parsed.responsibilities)
    if not output:
        output = lines
    return "\n".join(output).strip()


def _build_warnings(parsed: ParsedJobDescription) -> list[str]:
    warnings = []
    if not parsed.requiredSkills and not parsed.preferredSkills:
        warnings.append("No technical skills were confidently detected; review the JD manually.")
    if parsed.experienceRange.minYears is None:
        warnings.append("Experience range was not detected.")
    if not parsed.responsibilities:
        warnings.append("Responsibilities were not clearly detected.")
    return warnings
