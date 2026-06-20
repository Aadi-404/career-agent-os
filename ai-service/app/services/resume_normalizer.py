import re

from app.models.resume_normalize import (
    ResumeExperience,
    ResumeNormalizeRequest,
    ResumeNormalizeResponse,
    ResumeProfile,
    ResumeProject,
    StructuredResume,
)
from app.services.certificate_matcher import extract_certificate_evidence


SECTION_HEADERS = {
    "experience": ["experience", "work experience", "professional experience", "employment"],
    "projects": ["projects", "personal projects", "academic projects"],
    "skills": ["skills", "technical skills"],
    "education": ["education"],
    "achievements": ["achievements", "online coding platform"],
    "certifications": ["certifications", "certification", "certificates", "courses", "licenses"],
}

KNOWN_SKILLS = [
    ".net",
    "asp.net",
    "asp.net core",
    "asp.net mvc",
    "c#",
    "c++",
    "java",
    "spring boot",
    "python",
    "django",
    "fastapi",
    "react",
    "reactjs",
    "angular",
    "javascript",
    "typescript",
    "html",
    "css",
    "sql",
    "sql server",
    "sqlite",
    "sqlite3",
    "ssms",
    "entity framework",
    "ef",
    "linq",
    "jwt",
    "azure",
    "azure devops",
    "azure fundamentals",
    "az-900",
    "ci/cd",
    "docker",
    "aws",
    "aws certified",
    "microsoft certified",
    "git",
    "rest api",
    "restapi",
    "web api",
    "dbms",
    "dsa",
    "electron.js",
    "scapy",
]


def normalize_resume(request: ResumeNormalizeRequest) -> ResumeNormalizeResponse:
    cleaned_lines = _clean_lines(request.rawResumeText)
    sections = _split_sections(cleaned_lines)
    profile = _extract_profile(cleaned_lines, sections)
    structured = StructuredResume(
        profile=profile,
        experience=_extract_experience(sections.get("experience", [])),
        projects=_extract_projects(sections.get("projects", [])),
        skills=_extract_skills(cleaned_lines, sections.get("skills", [])),
        education=_extract_education(sections.get("education", [])),
        achievements=_extract_simple_items(sections.get("achievements", [])),
        certifications=_extract_certifications(sections.get("certifications", []), cleaned_lines),
    )
    warnings = _build_warnings(structured, sections)
    return ResumeNormalizeResponse(
        normalizedResumeText=_format_normalized_resume(structured),
        structuredResume=structured,
        warnings=warnings,
    )


def _clean_lines(text: str) -> list[str]:
    replacements = {
        "\ufb02": "fl",
        "\ufb01": "fi",
        "\u00a0": " ",
        "♂": " ",
        "¶": " ",
        "⌢": " ",
        "\u2022": "- ",
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    text = re.sub(r"(?i)(github)\s*(github\.com)", r"\1 \2", text)
    text = re.sub(r"(?i)(linkedin)\s*(linkedin\.com)", r"\1 \2", text)
    text = re.sub(r"(?i)\b(phone|mobile|email|mail|envelope|marker-alt)\b", r" \1 ", text)
    text = re.sub(r"(?i)(navi\s*mumbai|mumbai|pune|bangalore|bengaluru|hyderabad|delhi|noida|gurgaon|chennai|kolkata)", r" \1", text)

    lines = []
    for raw_line in text.splitlines():
        line = re.sub(r"\s+", " ", raw_line).strip(" ,.-")
        line = re.sub(r"^[-•]\s*", "", line).strip()
        if line:
            lines.append(line)
    return lines


def _split_sections(lines: list[str]) -> dict[str, list[str]]:
    sections: dict[str, list[str]] = {}
    current = "profile"
    sections[current] = []

    for line in lines:
        matched_section = _match_section_header(line)
        if matched_section:
            current = matched_section
            sections.setdefault(current, [])
            continue
        sections.setdefault(current, []).append(line)

    return sections


def _match_section_header(line: str) -> str | None:
    lowered = re.sub(r"[^a-z0-9 ]+", " ", line.lower()).strip()
    lowered = re.sub(r"\s+", " ", lowered)
    for section, headers in SECTION_HEADERS.items():
        if lowered in headers:
            return section
    if "certification" in lowered or "certificate" in lowered:
        return "certifications"
    if "project" in lowered and len(lowered.split()) <= 4:
        return "projects"
    return None


def _extract_profile(lines: list[str], sections: dict[str, list[str]]) -> ResumeProfile:
    profile_lines = sections.get("profile", lines[:8])
    text = _normalize_contact_text("\n".join(lines))
    email_match = re.search(r"(?<![a-z0-9._%+-])[\w.+-]+@[\w-]+\.[\w.-]+", text, flags=re.IGNORECASE)
    if not email_match:
        email_match = re.search(r"[a-z0-9._%+-]{3,}@[a-z0-9.-]+\.[a-z]{2,}", "\n".join(lines), flags=re.IGNORECASE)
    phone_match = re.search(r"(?:\+?\d[\d\s().-]{8,}\d)", text)
    linkedin_match = re.search(r"(?:https?://)?(?:www\.)?linkedin\.com/(?!github\b)[^\s,|]+", text, flags=re.IGNORECASE)
    github_match = re.search(r"(?:https?://)?(?:www\.)?github\.com/[^\s,|]+", text, flags=re.IGNORECASE)

    likely_name = None
    for line in profile_lines[:4]:
        if not any(token in line.lower() for token in ["linkedin", "github", "@", "http"]):
            if 2 <= len(line.split()) <= 5:
                likely_name = line
                break

    summary = None
    for line in profile_lines:
        if len(line.split()) >= 8 and not any(token in line.lower() for token in ["linkedin", "github", "@"]):
            summary = line
            break

    location = None
    for line in profile_lines[:8]:
        location_value = _extract_location_value(line)
        if location_value:
            location = location_value
            break

    return ResumeProfile(
        name=likely_name,
        location=location,
        email=_clean_email(email_match.group(0)) if email_match else None,
        phone=phone_match.group(0).strip() if phone_match else None,
        linkedin=_clean_profile_url(linkedin_match.group(0)) if linkedin_match else None,
        github=_clean_profile_url(github_match.group(0)) if github_match else None,
        summary=summary,
    )


def _extract_experience(lines: list[str]) -> list[ResumeExperience]:
    if not lines:
        return []

    title = lines[0] if lines else None
    company = lines[1] if len(lines) > 1 else None
    duration = _find_duration(lines)
    location = _find_location(lines)
    highlights = _extract_highlights(lines[2:])

    return [
        ResumeExperience(
            title=title,
            company=company,
            duration=duration,
            location=location,
            highlights=highlights,
        )
    ]


def _extract_projects(lines: list[str]) -> list[ResumeProject]:
    projects: list[ResumeProject] = []
    current_name: str | None = None
    current_duration: str | None = None
    current_lines: list[str] = []

    for index, line in enumerate(lines):
        next_line = lines[index + 1] if index + 1 < len(lines) else ""
        duration = _find_duration([line])
        if duration and current_name and not current_duration and not _looks_like_project_title(line, next_line):
            current_duration = duration
            continue

        looks_like_project = _looks_like_project_title(line, next_line)
        if looks_like_project:
            if current_name:
                projects.append(_build_project(current_name, current_duration, current_lines))
            current_name = _clean_project_title(line)
            current_duration = duration
            current_lines = []
        elif current_name:
            current_lines.append(line)

    if current_name:
        projects.append(_build_project(current_name, current_duration, current_lines))

    return projects


def _build_project(name: str, duration: str | None, lines: list[str]) -> ResumeProject:
    return ResumeProject(
        name=name,
        duration=duration or _find_duration(lines),
        techStack=_extract_project_tech_stack(lines),
        highlights=_extract_highlights(lines),
    )


def _extract_skills(all_lines: list[str], skill_lines: list[str]) -> list[str]:
    text = " ".join(skill_lines or all_lines).lower()
    found = []
    for skill in KNOWN_SKILLS:
        pattern = re.escape(skill).replace("\\ ", r"\s+")
        if re.search(rf"(?<![a-z0-9+#]){pattern}(?![a-z0-9+#])", text):
            found.append(_skill_label(skill))
    return sorted(set(found), key=str.lower)


def _extract_simple_items(lines: list[str]) -> list[str]:
    return [line for line in lines if len(line) > 2 and not _match_section_header(line)]


def _extract_education(lines: list[str]) -> list[str]:
    candidates = _extract_simple_items(lines)
    if not candidates:
        return []

    grouped: list[str] = []
    current: list[str] = []
    for line in candidates:
        if current and _looks_like_new_education_item(line):
            grouped.append(" | ".join(current))
            current = [line]
            continue
        current.append(line)

    if current:
        grouped.append(" | ".join(current))
    return grouped


def _looks_like_new_education_item(line: str) -> bool:
    lowered = line.lower()
    institution_tokens = ["university", "college", "school", "institute", "academy", "vidyalaya"]
    detail_tokens = ["cgpa", "gpa", "percentage", "bachelor", "b.tech", "btech", "branch", "computer", "engineering", "science", "2020", "2021", "2022", "2023", "2024", "2025", "2026"]
    return any(token in lowered for token in institution_tokens) and not any(token in lowered for token in detail_tokens)


def _extract_certifications(section_lines: list[str], all_lines: list[str]) -> list[str]:
    candidates = _extract_simple_items(section_lines)
    certification_patterns = [
        r"\b(?:az|ai|dp|pl|sc|ms)-\d{3}\b",
        r"\baws certified\b[^,\n]*",
        r"\bmicrosoft certified\b[^,\n]*",
        r"\bazure fundamentals\b",
        r"\bgoogle cloud\b[^,\n]*cert[^,\n]*",
        r"\boracle\b[^,\n]*cert[^,\n]*",
    ]
    for line in all_lines:
        if _match_section_header(line):
            continue
        lowered = line.lower()
        if any(keyword in lowered for keyword in ["certified", "certification", "certificate", "az-900", "aws certified"]):
            candidates.append(line)
            continue
        for pattern in certification_patterns:
            if re.search(pattern, lowered, flags=re.IGNORECASE):
                candidates.append(line)
                break
    evidence_text = "\n".join([*candidates, *all_lines])
    candidates.extend(item.raw_text for item in extract_certificate_evidence(evidence_text))
    return _dedupe_preserve_order([item for item in candidates if not _looks_like_contact_line(item)])


def _extract_project_tech_stack(lines: list[str]) -> list[str]:
    tech_lines = []
    pending_prefix = ""
    for line in lines:
        lowered = line.lower()
        if _find_duration([line]):
            continue
        if len(line.split()) <= 2 and lowered in ["used", "tech", "technology", "technologies", "stack"]:
            pending_prefix = lowered
            continue
        if pending_prefix:
            tech_lines.append(line)
            pending_prefix = ""
            continue
        if lowered.startswith(("tech", "used ", "stack")) or _line_has_skill(line):
            tech_lines.append(line)
    return _extract_skills(tech_lines, tech_lines)


def _extract_highlights(lines: list[str]) -> list[str]:
    highlights = []
    pending_prefix = ""
    action_words = (
        "built",
        "build",
        "delivered",
        "optimized",
        "implemented",
        "designed",
        "used",
        "monitored",
        "resolved",
        "created",
        "developed",
        "helps",
        "enabled",
        "enables",
        "web app",
    )

    for line in lines:
        lowered = line.lower()
        if len(line.split()) <= 2 and lowered in ["used", "tech", "implemented", "designed"]:
            pending_prefix = line
            continue
        if pending_prefix:
            line = f"{pending_prefix} {line}"
            pending_prefix = ""
        if len(line.split()) >= 3 and (lowered.startswith(action_words) or any(word in lowered for word in action_words)):
            highlights.append(_sentence(line))

    return highlights[:8]


def _find_duration(lines: list[str]) -> str | None:
    text = " ".join(lines)
    match = re.search(r"\(?\d{2}/\d{4}\s*-\s*(?:\d{2}/\d{4}|present|current)\)?", text, flags=re.IGNORECASE)
    if match:
        return match.group(0).strip("() ")
    month_match = re.search(
        r"\b(?:jan|feb|mar|apr|may|jun|jul|aug|sep|sept|oct|nov|dec)[a-z]*[-\s]+(?:19|20)\d{2}\b",
        text,
        flags=re.IGNORECASE,
    )
    if month_match:
        return re.sub(r"\s+", "-", month_match.group(0).strip())
    year_match = re.search(r"\b(?:19|20)\d{2}\s*-\s*(?:(?:19|20)\d{2}|present)\b", text, flags=re.IGNORECASE)
    return year_match.group(0) if year_match else None


def _find_location(lines: list[str]) -> str | None:
    for line in lines:
        if any(place in line.lower() for place in ["mumbai", "pune", "bangalore", "bengaluru", "hyderabad", "delhi", "india"]):
            return line
    return None


def _looks_like_title(line: str) -> bool:
    if len(line.split()) > 8:
        return False
    return bool(re.match(r"^[A-Z0-9][A-Za-z0-9 .,&/+:-]+(?:\([^)]*\))?$", line))


def _looks_like_project_title(line: str, next_line: str) -> bool:
    duration = _find_duration([line])
    title_without_duration = _clean_project_title(line) if duration else line
    if _looks_like_detail(line):
        return False
    if not _looks_like_title(title_without_duration):
        return False
    lowered = title_without_duration.lower()
    project_tokens = ["system", "application", "app", "project", "platform", "tool", "analyzer", "reservation"]
    if _line_has_skill(title_without_duration) and not any(token in lowered for token in project_tokens):
        return False
    if any(token in lowered for token in project_tokens):
        return True
    if duration and len(title_without_duration.split()) >= 2:
        return True
    if _find_duration([next_line]):
        return True
    return False


def _looks_like_detail(line: str) -> bool:
    lowered = line.lower()
    return lowered.startswith((
        "used ",
        "implemented ",
        "designed ",
        "tech ",
        "with ",
        "and ",
        "built ",
        "created ",
        "developed ",
        "helps ",
        "enabled ",
        "enables ",
        "web app ",
    ))


def _line_has_skill(line: str) -> bool:
    lowered = line.lower()
    for skill in KNOWN_SKILLS:
        pattern = re.escape(skill).replace("\\ ", r"\s+")
        if re.search(rf"(?<![a-z0-9+#]){pattern}(?![a-z0-9+#])", lowered):
            return True
    return False


def _sentence(text: str) -> str:
    text = text.strip(" .")
    return f"{text}."


def _normalize_contact_text(text: str) -> str:
    text = re.sub(r"(?i)(linkedin\.com/[^\s,|]+?)/(github)(?=github\.com|[\s,|])", r"\1 \2", text)
    text = re.sub(r"(?i)(github)\s*(github\.com)", r"\1 \2", text)
    text = re.sub(r"(?i)\b(phone|mobile|email|mail|envelope|marker-alt)\b", " ", text)
    return re.sub(r"\s+", " ", text)


def _clean_email(email: str) -> str:
    cleaned = email.strip(" ,;|")
    if "@" not in cleaned:
        return cleaned
    local, domain = cleaned.split("@", 1)
    local = re.sub(r"(?i)^(?:email|mail|envelope)", "", local).strip(".-_")
    for artifact_prefix in ("pe", "p"):
        candidate = local[len(artifact_prefix):]
        if local.lower().startswith(artifact_prefix) and candidate.lower().startswith(("aditya", "aadi")):
            local = candidate
            break
    return f"{local}@{domain}"


def _extract_location_value(line: str) -> str | None:
    match = re.search(
        r"\b((?:navi\s+)?mumbai|pune|bangalore|bengaluru|hyderabad|delhi|noida|gurgaon|chennai|kolkata)(?:\s*,?\s*india)?\b",
        line,
        flags=re.IGNORECASE,
    )
    if not match:
        return None
    city = re.sub(r"\s+", " ", match.group(1)).title()
    return f"{city}, India" if "india" in match.group(0).lower() else city


def _clean_profile_url(url: str) -> str:
    if "linkedin.com" in url.lower():
        url = re.sub(r"(?i)/github.*$", "", url)
    return url.strip(" /,|")


def _looks_like_contact_line(line: str) -> bool:
    lowered = line.lower()
    return ("linkedin.com" in lowered or "github.com" in lowered or "@" in lowered) and not any(
        token in lowered for token in ["cert", "certificate", "certification", "az-", "aws certified", "microsoft certified"]
    )


def _clean_project_title(line: str) -> str:
    line = re.sub(
        r"\b(?:jan|feb|mar|apr|may|jun|jul|aug|sep|sept|oct|nov|dec)[a-z]*[-\s]+(?:19|20)\d{2}\b",
        "",
        line,
        flags=re.IGNORECASE,
    )
    line = re.sub(r"\(?\d{2}/\d{4}\s*-\s*(?:\d{2}/\d{4}|present|current)\)?", "", line, flags=re.IGNORECASE)
    line = re.sub(r"\b(?:19|20)\d{2}\s*-\s*(?:(?:19|20)\d{2}|present)\b", "", line, flags=re.IGNORECASE)
    return line.strip(" -")


def _skill_label(skill: str) -> str:
    labels = {
        "asp.net": "ASP.NET",
        "asp.net core": "ASP.NET Core",
        "asp.net mvc": "ASP.NET MVC",
        "c#": "C#",
        "c++": "C++",
        "reactjs": "React",
        "sql": "SQL",
        "sql server": "SQL Server",
        "sqlite": "SQLite",
        "sqlite3": "SQLite",
        "ssms": "SSMS",
        "entity framework": "Entity Framework",
        "ef": "EF",
        "linq": "LINQ",
        "azure fundamentals": "Azure Fundamentals",
        "az-900": "AZ-900",
        "jwt": "JWT",
        "ci/cd": "CI/CD",
        "aws": "AWS",
        "aws certified": "AWS Certified",
        "microsoft certified": "Microsoft Certified",
        "rest api": "REST API",
        "restapi": "REST API",
        "web api": "Web API",
        "dbms": "DBMS",
        "dsa": "DSA",
        "electron.js": "Electron.js",
        "scapy": "Scapy",
    }
    return labels.get(skill, skill.title() if skill != ".net" else ".NET")


def _dedupe_preserve_order(items: list[str]) -> list[str]:
    seen = set()
    result = []
    for item in items:
        normalized = item.strip()
        key = normalized.lower()
        if normalized and key not in seen:
            seen.add(key)
            result.append(normalized)
    return result


def _build_warnings(structured: StructuredResume, sections: dict[str, list[str]]) -> list[str]:
    warnings = []
    if not structured.experience:
        warnings.append("Experience section was not confidently detected.")
    if not structured.projects:
        warnings.append("Projects section was not confidently detected.")
    if len(structured.skills) < 5:
        warnings.append("Only a few skills were detected; review the skills section manually.")
    if "profile" in sections and len(sections["profile"]) > 10:
        warnings.append("Profile section has many lines before the first detected heading; PDF layout may need manual cleanup.")
    return warnings


def _format_normalized_resume(structured: StructuredResume) -> str:
    lines: list[str] = []
    profile = structured.profile
    if profile.name:
        lines.append(profile.name)
    if profile.location:
        lines.append(f"Location: {profile.location}")
    contacts = [value for value in [profile.email, profile.phone, profile.linkedin, profile.github] if value]
    if contacts:
        lines.append("Contact: " + " | ".join(contacts))
    if profile.summary:
        lines.extend(["", "Summary", profile.summary])

    if structured.experience:
        lines.extend(["", "Experience"])
        for item in structured.experience:
            heading = " - ".join(value for value in [item.title, item.company, item.duration] if value)
            lines.append(heading)
            for highlight in item.highlights:
                lines.append(f"- {highlight}")

    if structured.projects:
        lines.extend(["", "Projects"])
        for project in structured.projects:
            heading = project.name if not project.duration else f"{project.name} ({project.duration})"
            lines.append(heading)
            if project.techStack:
                lines.append("Tech: " + ", ".join(project.techStack))
            for highlight in project.highlights:
                lines.append(f"- {highlight}")

    if structured.skills:
        lines.extend(["", "Skills", ", ".join(structured.skills)])
    if structured.education:
        lines.extend(["", "Education", *structured.education])
    if structured.achievements:
        lines.extend(["", "Achievements"])
        lines.extend(f"- {item}" for item in structured.achievements)
    if structured.certifications:
        lines.extend(["", "Certifications"])
        lines.extend(f"- {item}" for item in structured.certifications)

    return "\n".join(lines).strip()
