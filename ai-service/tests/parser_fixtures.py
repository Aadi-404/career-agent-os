from dataclasses import dataclass, field


@dataclass(frozen=True)
class ResumeParserExpectation:
    name: str | None = None
    email: str | None = None
    location: str | None = None
    experience_count: int | None = None
    project_names: list[str] = field(default_factory=list)
    project_highlight_counts: list[int] = field(default_factory=list)
    certification_count: int | None = None
    skills: list[str] = field(default_factory=list)
    parser_note_contains: str | None = None


@dataclass(frozen=True)
class ResumeParserFixture:
    id: str
    description: str
    raw_text: str
    expected: ResumeParserExpectation


@dataclass(frozen=True)
class JdParserExpectation:
    role_title_contains: str | None = None
    min_years: float | None = None
    required_skills: list[str] = field(default_factory=list)
    preferred_skills: list[str] = field(default_factory=list)
    required_certifications_contains: list[str] = field(default_factory=list)
    emphasized_contains: list[str] = field(default_factory=list)
    responsibilities_min_count: int | None = None
    locations: list[str] = field(default_factory=list)
    work_modes: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class JdParserFixture:
    id: str
    description: str
    raw_text: str
    expected: JdParserExpectation
