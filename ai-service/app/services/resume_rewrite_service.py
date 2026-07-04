from app.models.analysis import ResumeRewriteRequest, ResumeRewriteResponse, ResumeRewriteSuggestion, RequirementMatch


def build_resume_rewrite(request: ResumeRewriteRequest) -> ResumeRewriteResponse:
    matches = _priority_matches(request.analysis.requirementMatches)
    suggestions: list[ResumeRewriteSuggestion] = []
    for match in matches:
        if len(suggestions) >= request.limit:
            break
        suggestions.append(_suggestion_for_match(match))

    if not suggestions:
        suggestions.append(
            ResumeRewriteSuggestion(
                targetRequirement="Impact depth",
                evidenceSource="resume",
                originalEvidence=_first_resume_line(request.resumeText),
                currentIssue="Resume evidence is present, but impact can be clearer.",
                rewrittenBullet="Improved a relevant workflow by owning implementation details, validation, and measurable delivery impact.",
                proofSafety="needs_user_verification",
                reason="Use this only after replacing generic wording with your exact project, metric, and ownership.",
            )
        )

    warnings = [
        "Do not paste a rewritten bullet unless the original evidence is true.",
        "For gap-only suggestions, prepare or learn the topic; do not claim hands-on work.",
    ]
    return ResumeRewriteResponse(
        summary=f"Generated {len(suggestions)} evidence-constrained rewrite suggestion(s) from the current match matrix.",
        suggestions=suggestions,
        warnings=warnings,
    )


def _suggestion_for_match(match: RequirementMatch) -> ResumeRewriteSuggestion:
    if match.bestEvidence and match.evidenceSource != "missing":
        return ResumeRewriteSuggestion(
            targetRequirement=match.requirement,
            evidenceSource=match.evidenceSource,
            originalEvidence=match.bestEvidence,
            currentIssue=f"Evidence exists for {match.requirement}, but the bullet may not directly mirror the JD wording or impact.",
            rewrittenBullet=_rewrite_existing_evidence(match),
            proofSafety="safe_from_existing_evidence" if match.score >= 55 else "needs_user_verification",
            reason=f"Based on existing {match.evidenceSource} evidence. Match type: {match.matchType}.",
        )
    return ResumeRewriteSuggestion(
        targetRequirement=match.requirement,
        evidenceSource="missing",
        originalEvidence=None,
        currentIssue=f"The JD asks for {match.requirement}, but the current resume does not prove it.",
        rewrittenBullet=f"Do not claim {match.requirement} as experience unless you have real project proof; instead add a learning/preparation note or build a small proof project.",
        proofSafety="gap_do_not_claim",
        reason="The requirement is missing or too weak in the match matrix, so this is a preparation warning rather than a paste-ready resume bullet.",
    )


def _rewrite_existing_evidence(match: RequirementMatch) -> str:
    evidence = (match.bestEvidence or "").rstrip(".")
    requirement = match.requirement.rstrip(".")
    if match.score >= 75:
        return f"Delivered {requirement} work by {evidence}, highlighting ownership, implementation detail, and measurable outcome."
    return f"Strengthened {requirement} evidence through {evidence}; add the exact tool, scale, metric, or production result if truthful."


def _priority_matches(matches: list[RequirementMatch]) -> list[RequirementMatch]:
    return sorted(matches, key=lambda match: (_importance_rank(match.importance), match.score))


def _importance_rank(importance: str) -> int:
    if importance == "high":
        return 0
    if importance == "medium":
        return 1
    return 2


def _first_resume_line(text: str) -> str | None:
    for line in text.splitlines():
        cleaned = line.strip(" -\t")
        if len(cleaned) >= 20:
            return cleaned
    return None
