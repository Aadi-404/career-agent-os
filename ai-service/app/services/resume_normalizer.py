import re

from app.models.resume_normalize import (
    ResumeExperience,
    ResumeNormalizeRequest,
    ResumeNormalizeResponse,
    ResumeProfile,
    ResumeProject,
    StructuredResume,
)


SECTION_HEADERS = {
    "experience": ["experience", "work experience", "professional experience", "employment"],
    "projects": ["projects", "personal projects", "academic projects"],
    "skills": ["skills", "technical skills"],
    "education": ["education"],
    "achievements": ["achievements", "online coding platform"],
    "certifications": ["certifications", "certificates"],
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
    "ssms",
    "entity framework",
    "ef",
    "linq",
    "jwt",
    "azure",
    "azure devops",
    "ci/cd",
    "docker",
    "git",
    "rest api",
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
        education=_extract_simple_items(sections.get("education", [])),
        achievements=_extract_simple_items(sections.get("achievements", [])),
        certifications=_extract_simple_items(sections.get("certifications", [])),
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
    }
    for old, new in replacements.items():
        text = text.replace(old, new)

    lines = []
    for raw_line in text.splitlines():
        line = re.sub(r"\s+", " ", raw_line).strip(" ,.-")
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
    lowered = line.lower().strip(":")
    for section, headers in SECTION_HEADERS.items():
        if lowered in headers:
            return section
    return None


def _extract_profile(lines: list[str], sections: dict[str, list[str]]) -> ResumeProfile:
    profile_lines = sections.get("profile", lines[:8])
    text = "\n".join(lines)
    email_match = re.search(r"[\w.+-]+@[\w-]+\.[\w.-]+", text)
    phone_match = re.search(r"(?:\+?\d[\d\s().-]{8,}\d)", text)
    linkedin_match = re.search(r"(?:https?://)?(?:www\.)?linkedin\.com/[^\s,]+", text, flags=re.IGNORECASE)
    github_match = re.search(r"(?:https?://)?(?:www\.)?github\.com/[^\s,]+", text, flags=re.IGNORECASE)

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
        if any(place in line.lower() for place in ["mumbai", "pune", "bangalore", "bengaluru", "hyderabad", "delhi", "india"]):
            location = line
            break

    return ResumeProfile(
        name=likely_name,
        location=location,
        email=email_match.group(0) if email_match else None,
        phone=phone_match.group(0).strip() if phone_match else None,
        linkedin=linkedin_match.group(0) if linkedin_match else None,
        github=github_match.group(0) if github_match else None,
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

    for line in lines:
        looks_like_project = _looks_like_title(line) and not _looks_like_detail(line)
        if looks_like_project:
            if current_name:
                projects.append(_build_project(current_name, current_duration, current_lines))
            current_name = re.sub(r"\s*\([^)]*\)\s*$", "", line).strip()
            current_duration = _find_duration([line])
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
        techStack=_extract_skills(lines, lines),
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


def _looks_like_detail(line: str) -> bool:
    lowered = line.lower()
    return lowered.startswith(("used ", "implemented ", "designed ", "tech ", "with ", "and "))


def _sentence(text: str) -> str:
    text = text.strip(" .")
    return f"{text}."


def _skill_label(skill: str) -> str:
    labels = {
        "asp.net": "ASP.NET",
        "asp.net core": "ASP.NET Core",
        "asp.net mvc": "ASP.NET MVC",
        "c#": "C#",
        "c++": "C++",
        "reactjs": "React",
        "sql server": "SQL Server",
        "ssms": "SSMS",
        "entity framework": "Entity Framework",
        "ef": "EF",
        "linq": "LINQ",
        "jwt": "JWT",
        "ci/cd": "CI/CD",
        "rest api": "REST API",
        "web api": "Web API",
        "dbms": "DBMS",
        "dsa": "DSA",
    }
    return labels.get(skill, skill.title() if skill != ".net" else ".NET")


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
