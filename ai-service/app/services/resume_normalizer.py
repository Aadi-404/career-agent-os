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
    "express",
    "express.js",
    "expressjs",
    "node",
    "node.js",
    "nodejs",
    "react",
    "react.js",
    "reactjs",
    "angular",
    "js",
    "javascript",
    "typescript",
    "html",
    "css",
    "sql",
    "sql server",
    "postgres",
    "postgresql",
    "sqlite",
    "sqlite3",
    "ssms",
    "snowflake",
    "entity framework",
    "ef",
    "linq",
    "jwt",
    "azure",
    "azure devops",
    "azure data factory",
    "azure fundamentals",
    "adls",
    "az-900",
    "ci/cd",
    "control-m",
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
    inline_projects = _extract_inline_project_blocks(cleaned_lines)
    experience_lines = _strip_inline_project_blocks(sections.get("experience", [])) if inline_projects else sections.get("experience", [])
    experience = _extract_experience(experience_lines)
    projects = _extract_projects(sections.get("projects", []))
    if inline_projects:
        projects = inline_projects
    if not projects:
        projects = _extract_project_fallback(cleaned_lines, experience)
    structured = StructuredResume(
        profile=profile,
        experience=experience,
        projects=projects,
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
    text = _normalize_dash_artifacts(text)
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
    text = text.replace("–", "-").replace("—", "-").replace("â€“", "-").replace("â€”", "-")
    text = re.sub(r"(?i)(github)\s*(github\.com)", r"\1 \2", text)
    text = re.sub(r"(?i)(linkedin)\s*(linkedin\.com)", r"\1 \2", text)
    text = re.sub(r"(?i)\b(phone|mobile|email|mail|envelope|marker-alt)\b", r" \1 ", text)
    text = re.sub(r"(?i)(navi\s*mumbai|mumbai|pune|bangalore|bengaluru|hyderabad|delhi|noida|gurgaon|chennai|kolkata)", r" \1", text)

    lines = []
    for raw_line in text.splitlines():
        line = re.sub(r"\s+", " ", raw_line).strip(" ,.-")
        line = re.sub(
            r"(?i)([a-z)])((?:jan|feb|mar|apr|may|jun|jul|aug|sep|sept|oct|nov|dec)[a-z]*\s+(?:19|20)\d{2})",
            r"\1 \2",
            line,
        )
        line = re.sub(r"(?i)\bnavi\s*-\s*mumbai\b", "Navi Mumbai", line)
        line = re.sub(r"^[-•]\s*", "", line).strip()
        if line:
            lines.append(line)
    return lines


def _normalize_dash_artifacts(text: str) -> str:
    for dash in ["\u2010", "\u2011", "\u2012", "\u2013", "\u2014", "\u2212"]:
        text = text.replace(dash, "-")
    return re.sub(
        r"(?i)\b((?:jan|feb|mar|apr|may|jun|jul|aug|sep|sept|oct|nov|dec)[a-z]*\s+(?:19|20)\d{2})\s*\?\s*((?:(?:jan|feb|mar|apr|may|jun|jul|aug|sep|sept|oct|nov|dec)[a-z]*\s+(?:19|20)\d{2})|present|current)\b",
        r"\1 - \2",
        text,
    )


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

    experiences = []
    for block in _split_experience_blocks(lines):
        expanded_lines = _expand_experience_lines(block)
        if not expanded_lines:
            continue
        title = _extract_experience_title(expanded_lines)
        company = _extract_company(expanded_lines)
        duration = _find_duration(expanded_lines)
        location = _find_location(expanded_lines, company)
        highlights = _extract_highlights(_experience_detail_lines(expanded_lines))
        experiences.append(
            ResumeExperience(
                title=title,
                company=company,
                duration=duration,
                location=location,
                highlights=highlights,
            )
        )

    return experiences


def _split_experience_blocks(lines: list[str]) -> list[list[str]]:
    blocks: list[list[str]] = []
    current: list[str] = []

    for index, line in enumerate(lines):
        next_line = lines[index + 1] if index + 1 < len(lines) else ""
        following_line = lines[index + 2] if index + 2 < len(lines) else ""
        if current and (_looks_like_experience_header(line) or _looks_like_stacked_experience_header(line, next_line, following_line)):
            blocks.append(current)
            current = [line]
            continue
        current.append(line)

    if current:
        blocks.append(current)
    return blocks


def _looks_like_experience_header(line: str) -> bool:
    if not _find_duration([line]):
        return False
    lowered = line.lower()
    if _looks_like_detail(line):
        return False
    if any(token in lowered for token in ["built ", "developed ", "designed ", "implemented ", "improved ", "optimized ", "created "]):
        return False
    before_duration = _before_duration(line).strip(" ,|-")
    after_duration = _after_duration(line).strip(" ,|-")
    if len(before_duration.split()) > 6 or len(before_duration.split()) == 0:
        return False
    if "|" in after_duration or _extract_location_value(after_duration):
        return True
    title_part = re.split(r"\s+-\s+", after_duration, maxsplit=1)[0].strip(" ,|-")
    return 1 <= len(title_part.split()) <= 6 and not _looks_like_detail(title_part)


def _looks_like_stacked_experience_header(line: str, next_line: str, following_line: str) -> bool:
    if _find_duration([line]) or _looks_like_detail(line) or not _looks_like_title(line):
        return False
    if not _looks_like_role_title(line):
        return False
    if not next_line or _looks_like_detail(next_line) or _match_section_header(next_line):
        return False
    if len(line.split()) > 5 or len(next_line.split()) > 6:
        return False
    return _find_duration([next_line]) is not None or _find_duration([following_line]) is not None


def _looks_like_role_title(line: str) -> bool:
    lowered = line.lower()
    role_tokens = [
        "analyst",
        "architect",
        "consultant",
        "developer",
        "engineer",
        "intern",
        "lead",
        "manager",
        "programmer",
        "specialist",
    ]
    return any(token in lowered for token in role_tokens)


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


def _extract_inline_project_blocks(lines: list[str]) -> list[ResumeProject]:
    projects: list[ResumeProject] = []
    current_name: str | None = None
    current_lines: list[str] = []

    for line in lines:
        if _looks_like_explicit_project_heading(line):
            if current_name:
                projects.append(_build_project(current_name, None, current_lines))
            current_name = line
            current_lines = []
            continue

        if current_name:
            if _match_section_header(line) and _match_section_header(line) != "projects":
                projects.append(_build_project(current_name, None, current_lines))
                current_name = None
                current_lines = []
                continue
            if _looks_like_resume_boundary(line):
                projects.append(_build_project(current_name, None, current_lines))
                current_name = None
                current_lines = []
                continue
            current_lines.append(line)

    if current_name:
        projects.append(_build_project(current_name, None, current_lines))

    return [project for project in projects if project.highlights][:4]


def _strip_inline_project_blocks(lines: list[str]) -> list[str]:
    kept = []
    in_project_block = False
    for line in lines:
        if _looks_like_explicit_project_heading(line):
            in_project_block = True
            continue
        if in_project_block:
            if _match_section_header(line) or _looks_like_resume_boundary(line):
                in_project_block = False
                kept.append(line)
            continue
        kept.append(line)
    return kept


def _extract_project_fallback(all_lines: list[str], experience: list[ResumeExperience]) -> list[ResumeProject]:
    candidate_lines = []
    candidate_lines.extend(
        line
        for line in all_lines
        if _looks_like_project_achievement(line) and not _looks_like_certification_line(line) and not (_find_duration([line]) and "|" in line) and _looks_like_explicit_project_heading_or_detail(line)
    )

    projects_by_name: dict[str, ResumeProject] = {}
    for line in _dedupe_preserve_order(candidate_lines):
        name = _infer_project_name(line)
        if not name:
            continue
        if name in projects_by_name:
            projects_by_name[name].highlights.append(_sentence(line))
            projects_by_name[name].techStack = _dedupe_preserve_order([*projects_by_name[name].techStack, *_extract_project_tech_stack([line])])
            continue
        projects_by_name[name] = ResumeProject(
                name=name,
                duration=None,
                techStack=_extract_project_tech_stack([line]),
                highlights=[_sentence(line)],
        )
    return list(projects_by_name.values())[:4]


def _build_project(name: str, duration: str | None, lines: list[str]) -> ResumeProject:
    clean_name, heading_tech = _split_project_heading(name)
    return ResumeProject(
        name=clean_name,
        duration=duration or _find_duration(lines),
        techStack=_dedupe_preserve_order([*heading_tech, *_extract_project_tech_stack(lines)]),
        highlights=_extract_highlights(lines),
    )


def _split_project_heading(name: str) -> tuple[str, list[str]]:
    if "|" not in name:
        return name, []
    project_name, tech_text = [part.strip() for part in name.split("|", 1)]
    return project_name, _extract_skills([tech_text], [tech_text])


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
    candidates = [line for line in _extract_simple_items(section_lines) if _looks_like_certification_line(line)]
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
        if _looks_like_certification_line(line):
            candidates.append(line)
            continue
        for pattern in certification_patterns:
            if re.search(pattern, lowered, flags=re.IGNORECASE):
                candidates.append(line)
                break
    evidence_text = "\n".join([*candidates, *all_lines])
    candidates.extend(item.raw_text for item in extract_certificate_evidence(evidence_text))
    return _dedupe_certifications([item for item in candidates if _looks_like_certification_line(item) and not _looks_like_contact_line(item)])


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
        "integrated",
        "designed",
        "used",
        "monitored",
        "resolved",
        "created",
        "developed",
        "improved",
        "helps",
        "enabled",
        "enables",
        "web app",
        "data validation",
        "dashboard",
        "etl",
        "ai agent",
    )

    for line in lines:
        lowered = line.lower()
        if len(line.split()) <= 2 and lowered in ["used", "tech", "implemented", "designed"]:
            pending_prefix = line
            continue
        if pending_prefix:
            line = f"{pending_prefix} {line}"
            pending_prefix = ""
        for sentence in _split_compound_sentences(line):
            sentence_lowered = sentence.lower()
            if len(sentence.split()) >= 3 and (sentence_lowered.startswith(action_words) or any(word in sentence_lowered for word in action_words)):
                highlights.append(_sentence(sentence))

    return highlights[:8]


def _find_duration(lines: list[str]) -> str | None:
    text = " ".join(lines)
    text = _normalize_dash_artifacts(text)
    text = text.replace("–", "-").replace("—", "-")
    match = re.search(r"\(?\d{2}/\d{4}\s*-\s*(?:\d{2}/\d{4}|present|current)\)?", text, flags=re.IGNORECASE)
    if match:
        return match.group(0).strip("() ")
    range_month_match = re.search(
        r"\b(?:jan|feb|mar|apr|may|jun|jul|aug|sep|sept|oct|nov|dec)[a-z]*\s+(?:19|20)\d{2}\s*-\s*(?:(?:jan|feb|mar|apr|may|jun|jul|aug|sep|sept|oct|nov|dec)[a-z]*\s+(?:19|20)\d{2}|present|current)\b",
        text,
        flags=re.IGNORECASE,
    )
    if range_month_match:
        return re.sub(r"\s*-\s*", " - ", re.sub(r"\s+", " ", range_month_match.group(0).strip()))
    month_match = re.search(
        r"\b(?:jan|feb|mar|apr|may|jun|jul|aug|sep|sept|oct|nov|dec)[a-z]*[-\s]+(?:19|20)\d{2}\b",
        text,
        flags=re.IGNORECASE,
    )
    if month_match:
        return re.sub(r"\s+", "-", month_match.group(0).strip())
    year_match = re.search(r"\b(?:19|20)\d{2}\s*-\s*(?:(?:19|20)\d{2}|present)\b", text, flags=re.IGNORECASE)
    return year_match.group(0) if year_match else None


def _extract_company(lines: list[str]) -> str | None:
    if len(lines) >= 2 and lines[1].lower().startswith("title"):
        return lines[0].strip(" ,|-") or None
    if len(lines) >= 2 and _find_duration([lines[1]]) and not _find_duration([lines[0]]):
        return lines[0].strip(" ,|-") or None
    if len(lines) >= 3 and _find_duration([lines[1]]) and lines[2].lower().startswith("title"):
        return lines[0].strip(" ,|-") or None
    for line in lines[:3]:
        if _find_duration([line]):
            before_duration = _before_duration(line)
            cleaned = re.sub(r"(?i)^company\s*[-:>]*\s*", "", before_duration).strip(" ,|-")
            if cleaned:
                return cleaned
    if len(lines) < 2:
        return None
    company_line = _remove_duration(lines[1])
    location = _extract_location_value(company_line)
    if location:
        company_line = re.sub(re.escape(location), "", company_line, flags=re.IGNORECASE)
        company_line = re.sub(r"\b(?:navi\s+)?mumbai|pune|bangalore|bengaluru|hyderabad|delhi|india\b", "", company_line, flags=re.IGNORECASE)
    return company_line.strip(" ,|-") or None


def _find_location(lines: list[str], company: str | None = None) -> str | None:
    for line in lines:
        location = _extract_location_value(line)
        if location:
            return location
    return None


def _extract_experience_title(lines: list[str]) -> str | None:
    for line in lines[:6]:
        lowered = line.lower()
        if lowered.startswith("title"):
            return _clean_experience_title(line)
    for line in lines[:6]:
        if "|" in line and _extract_location_value(line):
            title_part = line.split("|", 1)[0].strip(" ,|-")
            if title_part and not _find_duration([title_part]):
                return title_part
    for line in lines[:6]:
        if _find_duration([line]) and "-" in line:
            after_duration = _after_duration(line)
            title_part = re.split(r"\||\b(?:navi\s+)?mumbai|pune|bangalore|bengaluru|hyderabad|delhi\b", after_duration, flags=re.IGNORECASE)[0]
            title_part = title_part.strip(" ,|-")
            if title_part and not _looks_like_detail(title_part):
                return title_part
    return _clean_experience_title(lines[0]) if lines else None


def _experience_detail_lines(lines: list[str]) -> list[str]:
    details = []
    for line in lines:
        for part in _split_compound_sentences(line):
            if _looks_like_detail(part) or _looks_like_project_achievement(part):
                details.append(part)
    return details or lines[2:]


def _looks_like_resume_boundary(line: str) -> bool:
    lowered = re.sub(r"[^a-z0-9 ]+", " ", line.lower()).strip()
    lowered = re.sub(r"\s+", " ", lowered)
    return lowered in {"skills", "education", "certifications", "certification", "achievements", "experience", "summary"}


def _expand_experience_lines(lines: list[str]) -> list[str]:
    expanded = []
    for line in lines:
        if _find_duration([line]) and any(token in line.lower() for token in [" - ", "|", " built ", " designed ", " developed "]):
            expanded.extend(_split_experience_compound_line(line))
        else:
            expanded.append(line)
    return [line for line in expanded if line.strip()]


def _split_experience_compound_line(line: str) -> list[str]:
    duration = _find_duration([line])
    if not duration:
        return [line]

    before = _before_duration(line).strip(" ,|-")
    after = _after_duration(line).strip(" ,|-")
    parts = [before] if before else []
    parts.append(duration)

    title_part = after
    location_part = ""
    if "|" in after:
        title_part, location_part = [part.strip(" ,|-") for part in after.split("|", 1)]
    else:
        location_match = re.search(r"\b(?:navi\s+)?mumbai|pune|bangalore|bengaluru|hyderabad|delhi\b(?:\s*,?\s*india)?", after, flags=re.IGNORECASE)
        if location_match:
            title_part = after[: location_match.start()].strip(" ,|-")
            location_part = after[location_match.start() :].strip(" ,|-")

    if title_part:
        parts.append(f"Title: {title_part}")
    if location_part:
        location_only = re.split(r"\s+-\s+", location_part, maxsplit=1)[0].strip(" ,|-")
        parts.append(location_only)

    details_source = re.split(r"\s+-\s+", after, maxsplit=2)
    for detail in (details_source[2:] if len(details_source) > 2 else []):
        parts.extend(_split_compound_sentences(detail))
    return parts


def _clean_experience_title(line: str) -> str:
    line = re.sub(r"(?i)^title\s*[-:>]*\s*", "", line)
    return _remove_duration(line).strip(" ,|-")


def _remove_duration(line: str) -> str:
    duration = _find_duration([line])
    if duration:
        line = line.replace(duration, "")
        line = line.replace(duration.replace(" - ", "-"), "")
    line = re.sub(
        r"\b(?:jan|feb|mar|apr|may|jun|jul|aug|sep|sept|oct|nov|dec)[a-z]*\s+(?:19|20)\d{2}\s*[-–—]\s*(?:(?:jan|feb|mar|apr|may|jun|jul|aug|sep|sept|oct|nov|dec)[a-z]*\s+(?:19|20)\d{2}|present|current)\b",
        "",
        line,
        flags=re.IGNORECASE,
    )
    return line.strip(" ,|-")


def _before_duration(line: str) -> str:
    duration = _find_duration([line])
    if not duration:
        return line
    match = re.search(re.escape(duration).replace("\\ \\-\\ ", r"\s*-\s*"), line, flags=re.IGNORECASE)
    return line[: match.start()] if match else line.split(duration, 1)[0]


def _after_duration(line: str) -> str:
    duration = _find_duration([line])
    if not duration:
        return line
    pattern = re.escape(duration).replace("\\ \\-\\ ", r"\s*-\s*")
    match = re.search(pattern, line, flags=re.IGNORECASE)
    return line[match.end() :] if match else line.split(duration, 1)[-1]


def _split_compound_sentences(line: str) -> list[str]:
    cleaned = re.sub(r"\s+-\s+(?=(?:built|designed|developed|delivered|created|reduced|cutting|eliminating|improving|and data validation)\b)", "\n", line, flags=re.IGNORECASE)
    parts = re.split(r"\n|(?<=[.])\s+", cleaned)
    return [part.strip(" -") for part in parts if part.strip(" -")]


def _looks_like_certification_line(line: str) -> bool:
    lowered = line.lower()
    if lowered.strip(" :-") in {"certification", "certifications", "certificate", "certificates"}:
        return False
    if lowered.startswith(("holds multiple", "validating deep expertise")):
        return False
    if _looks_like_certification_noise(line):
        return False
    return bool(
        re.search(r"\b(?:az|ai|dp|pl|sc|ms)-\d{3}\b", lowered)
        or "certified" in lowered
        or "certification" in lowered
        or "certificate" in lowered
    )


def _looks_like_certification_noise(line: str) -> bool:
    lowered = line.lower()
    if re.search(r"\b(?:az|ai|dp|pl|sc|ms)-\d{3}\b", lowered):
        return False
    if re.search(r"\b(?:microsoft|aws|google|oracle|salesforce|snowflake)\s+certified\b", lowered):
        return False
    if re.search(r"\bcertified\s*:", lowered):
        return False
    action_prefixes = (
        "built ",
        "created ",
        "developed ",
        "designed ",
        "implemented ",
        "improved ",
        "reduced ",
        "validated ",
        "validating ",
    )
    return lowered.startswith(action_prefixes)


def _looks_like_project_achievement(line: str) -> bool:
    lowered = line.lower()
    project_terms = [
        "web application",
        "web applications",
        "etl",
        "dashboard",
        "dashboards",
        "ai agent",
        "ai agents",
        "automation workflow",
        "data validation",
        "unified interface",
        "api",
        "apis",
    ]
    action_terms = ["built", "designed", "developed", "deployed", "reduced", "cutting", "eliminating", "processing"]
    return any(term in lowered for term in project_terms) and any(term in lowered for term in action_terms)


def _infer_project_name(line: str) -> str | None:
    lowered = line.lower()
    if "etl" in lowered or "dashboard" in lowered or "power bi" in lowered:
        return "ETL and Power BI Reporting"
    if "ai agent" in lowered or "automation workflow" in lowered:
        return "AI Agents and Automation Workflows"
    if "data validation" in lowered or "unified interface" in lowered or "cross-database" in lowered:
        return "Data Validation Interface"
    if "web application" in lowered or "web applications" in lowered or "api" in lowered:
        return "Enterprise Web Applications"
    return None


def _looks_like_title(line: str) -> bool:
    if len(line.split()) > 8:
        return False
    return bool(re.match(r"^[A-Z0-9][A-Za-z0-9 .,&/+:-]+(?:\([^)]*\))?$", line))


def _looks_like_project_title(line: str, next_line: str) -> bool:
    if _looks_like_explicit_project_heading(line):
        return True
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


def _looks_like_explicit_project_heading(line: str) -> bool:
    if "|" not in line:
        return False
    name, tech = [part.strip() for part in line.split("|", 1)]
    if not name or not tech or len(name.split()) > 8:
        return False
    if _extract_location_value(tech):
        return False
    return _line_has_skill(tech)


def _looks_like_explicit_project_heading_or_detail(line: str) -> bool:
    return _looks_like_explicit_project_heading(line) or any(
        token in line.lower()
        for token in ["data simplified tool", "ai agents platform", "sttm file parser"]
    )


def _looks_like_detail(line: str) -> bool:
    lowered = line.lower()
    return lowered.startswith((
        "used ",
        "implemented ",
        "integrated ",
        "designed ",
        "tech ",
        "with ",
        "and ",
        "built ",
        "created ",
        "developed ",
        "delivered ",
        "reduced ",
        "resolved ",
        "cut ",
        "cutting ",
        "eliminated ",
        "eliminating ",
        "improved ",
        "improving ",
        "optimized ",
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
        "express": "Express.js",
        "express.js": "Express.js",
        "expressjs": "Express.js",
        "js": "JavaScript",
        "javascript": "JavaScript",
        "typescript": "TypeScript",
        "react": "React",
        "react.js": "React",
        "reactjs": "React",
        "node": "Node.js",
        "node.js": "Node.js",
        "nodejs": "Node.js",
        "postgres": "PostgreSQL",
        "postgresql": "PostgreSQL",
        "sql": "SQL",
        "sql server": "SQL Server",
        "sqlite": "SQLite",
        "sqlite3": "SQLite",
        "ssms": "SSMS",
        "snowflake": "Snowflake",
        "entity framework": "Entity Framework",
        "ef": "EF",
        "linq": "LINQ",
        "azure data factory": "Azure Data Factory",
        "azure fundamentals": "Azure Fundamentals",
        "adls": "ADLS",
        "az-900": "AZ-900",
        "jwt": "JWT",
        "ci/cd": "CI/CD",
        "control-m": "Control-M",
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


def _dedupe_certifications(items: list[str]) -> list[str]:
    seen = set()
    result = []
    for item in items:
        normalized = item.strip()
        key = re.sub(r"\s+", " ", normalized.lower())
        key = re.sub(r"\s+[?-]\s+microsoft$", "", key)
        key = re.sub(r"\s+[?-]\s+amazon web services$", "", key)
        key = re.sub(r"\s+[?-]\s+aws$", "", key)
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
