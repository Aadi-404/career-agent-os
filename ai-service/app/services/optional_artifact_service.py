from app.models.analysis import (
    AnalysisResponse,
    AnalyzeRequest,
    CrossQuestion,
    InterviewQuestion,
    RequirementMatch,
    ResumeImprovement,
)


def build_resume_improvements(
    request: AnalyzeRequest,
    analysis: AnalysisResponse,
    limit: int,
) -> list[ResumeImprovement]:
    weak_or_missing = _weak_or_missing(analysis.requirementMatches)
    if not weak_or_missing:
        return [
            ResumeImprovement(
                currentIssue="Resume evidence mostly aligns with the extracted JD requirements.",
                suggestedBullet="Add one measurable result to the most relevant project so the recruiter can see impact, not only responsibility.",
                reason="Strong matches still improve when backed by numbers, ownership, and outcome.",
            )
        ]

    return [
        ResumeImprovement(
            currentIssue=f"Weak or missing evidence for: {match.requirement}",
            suggestedBullet=f"Add a truthful bullet showing where you used or prepared {match.requirement}, including project context and outcome.",
            reason=(
                f"The JD requirement is marked {match.importance} importance. "
                f"Current evidence source: {match.evidenceSource}. {match.reason}"
            ),
        )
        for match in weak_or_missing[:limit]
    ]


def build_interview_questions(
    request: AnalyzeRequest,
    analysis: AnalysisResponse,
    limit: int,
) -> list[InterviewQuestion]:
    selected = _priority_matches(analysis.requirementMatches)[:limit]
    if not selected:
        selected = analysis.requirementMatches[:limit]

    return [
        InterviewQuestion(
            topic=match.requirement,
            question=f"Explain your practical experience with {match.requirement}.",
            difficulty=_difficulty(match),
            expectedFocus=(
                "Give project context, your exact responsibility, implementation details, "
                "tradeoffs, debugging/testing, and measurable outcome."
            ),
        )
        for match in selected
    ]


def build_cross_questions(
    request: AnalyzeRequest,
    analysis: AnalysisResponse,
    limit: int,
) -> list[CrossQuestion]:
    selected = _priority_matches(analysis.requirementMatches)[:limit]
    if not selected:
        selected = analysis.requirementMatches[:limit]

    questions: list[CrossQuestion] = []
    for match in selected:
        questions.extend(
            [
                CrossQuestion(
                    question=f"Where exactly is {match.requirement} proven in your resume?",
                    whyAsked="Interviewers check whether a claimed JD match is real hands-on work or only keyword familiarity.",
                    expectedAnswerHint="Point to one project or work item, explain your role, and describe the result or learning.",
                ),
                CrossQuestion(
                    question=f"What tradeoff or limitation did you face while working with {match.requirement}?",
                    whyAsked="Follow-up questions test depth beyond definitions and tool names.",
                    expectedAnswerHint="Mention a constraint, decision, failure, debugging step, or improvement you can defend.",
                ),
            ]
        )
    return questions[:limit]


def _priority_matches(matches: list[RequirementMatch]) -> list[RequirementMatch]:
    return sorted(
        matches,
        key=lambda match: (_importance_rank(match.importance), match.score),
    )


def _weak_or_missing(matches: list[RequirementMatch]) -> list[RequirementMatch]:
    return [match for match in _priority_matches(matches) if match.score < 60]


def _importance_rank(importance: str) -> int:
    if importance == "high":
        return 0
    if importance == "medium":
        return 1
    return 2


def _difficulty(match: RequirementMatch) -> str:
    if match.importance == "high" and match.score < 45:
        return "hard"
    if match.importance == "high" or match.score < 65:
        return "medium"
    return "easy"
