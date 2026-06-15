import re

from app.models.jd_parse import ExperienceRange, JdParseRequest, JdParseResponse, ParsedJobDescription


SKILL_ALIASES: dict[str, list[str]] = {
    ".NET": [".net", "dotnet"],
    "ASP.NET": ["asp.net", "asp net"],
    "ASP.NET Core": ["asp.net core", "asp net core"],
    "ASP.NET MVC": ["asp.net mvc", "mvc"],
    "C#": ["c#"],
    "Java": ["java"],
    "Spring Boot": ["spring boot"],
    "Python": ["python"],
    "Web API": ["web api", "rest api", "restapi", "restful api"],
    "SQL": ["sql"],
    "SQL Server": ["sql server", "ssms"],
    "SQLite": ["sqlite", "sqlite3"],
    "Entity Framework": ["entity framework", "ef core", "ef"],
    "LINQ": ["linq"],
    "Angular": ["angular"],
    "React": ["react", "reactjs"],
    "JavaScript": ["javascript", "jquery", "js"],
    "TypeScript": ["typescript"],
    "HTML": ["html"],
    "CSS": ["css"],
    "Azure": ["azure", "azure cloud"],
    "Azure DevOps": ["azure devops", "ci/cd", "pipeline", "pipelines"],
    "Azure Fundamentals": ["azure fundamentals", "az-900"],
    "AWS Certification": ["aws certified", "aws certification"],
    "Microsoft Certification": ["microsoft certified", "microsoft certification"],
    "Certification": ["certification", "certified", "certificate"],
    "Docker": ["docker"],
    "Git": ["git"],
    "Authentication": ["jwt", "authentication", "authorization"],
    "System Design": ["system design", "scalable", "architecture", "distributed"],
}

LOCATIONS = [
    "navi mumbai",
    "mumbai",
    "pune",
    "bangalore",
    "bengaluru",
    "hyderabad",
    "chennai",
    "delhi",
    "noida",
    "gurgaon",
    "remote",
]

WORK_MODES = {
    "remote": ["remote", "work from home", "wfh"],
    "hybrid": ["hybrid"],
    "onsite": ["onsite", "on-site", "work from office", "wfo"],
}


def parse_jd(request: JdParseRequest) -> JdParseResponse:
    lines = _clean_lines(request.rawJobDescriptionText)
    text = "\n".join(lines)
    parsed = ParsedJobDescription(
        roleTitle=_extract_role_title(lines),
        experienceRange=_extract_experience_range(text),
        requiredSkills=_extract_required_skills(text),
        preferredSkills=_extract_preferred_skills(text),
        requiredCertifications=_extract_required_certifications(text),
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
    range_match = re.search(r"(\d+)\s*(?:-|to)\s*(\d+)\s*(?:years?|yrs?)", lowered)
    if range_match:
        return ExperienceRange(minYears=int(range_match.group(1)), maxYears=int(range_match.group(2)))
    min_match = re.search(r"(?:minimum|min|at least)\s*(\d+)\s*(?:years?|yrs?)", lowered)
    if min_match:
        return ExperienceRange(minYears=int(min_match.group(1)))
    single_match = re.search(r"(\d+)\+?\s*(?:years?|yrs?)", lowered)
    if single_match:
        return ExperienceRange(minYears=int(single_match.group(1)))
    return ExperienceRange()


def _extract_required_skills(text: str) -> list[str]:
    found = _extract_skills(text)
    high_signal = []
    lowered = text.lower()
    required_sentences = [
        sentence
        for sentence in _sentences(lowered)
        if any(token in sentence for token in ["must have", "required", "mandatory", "should have"])
        and not any(token in sentence for token in ["good to have", "nice to have", "preferred"])
    ]
    for skill in found:
        aliases = SKILL_ALIASES[skill]
        if any(any(_contains_phrase(sentence, alias) for alias in aliases) for sentence in required_sentences):
            high_signal.append(skill)
    if high_signal:
        return sorted(set(high_signal), key=str.lower)
    return found[:10]


def _extract_preferred_skills(text: str) -> list[str]:
    found = _extract_skills(text)
    required = set(_extract_required_skills(text))
    preferred = [skill for skill in found if skill not in required]
    lowered = text.lower()
    explicit_preferred = []
    for skill in preferred:
        aliases = SKILL_ALIASES[skill]
        if any(f"preferred {alias}" in lowered or f"good to have {alias}" in lowered for alias in aliases):
            explicit_preferred.append(skill)
    return sorted(set(explicit_preferred or preferred), key=str.lower)


def _extract_required_certifications(text: str) -> list[str]:
    lowered = text.lower()
    certifications = []
    required_text = " ".join(
        sentence
        for sentence in _sentences(lowered)
        if any(token in sentence for token in ["must have", "required", "mandatory", "should have"])
        and not any(token in sentence for token in ["good to have", "nice to have", "preferred"])
    )
    certification_patterns = {
        "AZ-900 / Azure Fundamentals": [r"\baz-900\b", r"\bazure fundamentals\b"],
        "AWS Certified": [r"\baws certified\b", r"\baws certification\b"],
        "Microsoft Certified": [r"\bmicrosoft certified\b", r"\bmicrosoft certification\b"],
        "Certification Required": [r"\bcertification required\b", r"\bcertified\b", r"\bcertification\b"],
    }
    for label, patterns in certification_patterns.items():
        if required_text and any(re.search(pattern, required_text) for pattern in patterns):
            certifications.append(label)
    return certifications


def _extract_skills(text: str) -> list[str]:
    lowered = text.lower()
    found = []
    for skill, aliases in SKILL_ALIASES.items():
        if any(_contains_phrase(lowered, alias) for alias in aliases):
            found.append(skill)
    return sorted(set(found), key=str.lower)


def _contains_phrase(text: str, phrase: str) -> bool:
    escaped = re.escape(phrase).replace("\\ ", r"\s+")
    return bool(re.search(rf"(?<![a-z0-9+#]){escaped}(?![a-z0-9+#])", text))


def _sentences(text: str) -> list[str]:
    return [part.strip() for part in re.split(r"(?:[.!?]\s+|[\n;])", text) if part.strip()]


def _extract_responsibilities(lines: list[str]) -> list[str]:
    responsibilities = []
    action_words = (
        "build",
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
        lowered = line.lower()
        if lowered.startswith(action_words) or any(f" {word} " in f" {lowered} " for word in action_words):
            responsibilities.append(_sentence(line))
    return responsibilities[:8]


def _extract_locations(text: str) -> list[str]:
    lowered = text.lower()
    return sorted({location.title() for location in LOCATIONS if location in lowered})


def _extract_work_modes(text: str) -> list[str]:
    lowered = text.lower()
    found = []
    for mode, aliases in WORK_MODES.items():
        if any(alias in lowered for alias in aliases):
            found.append(mode)
    return found


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
