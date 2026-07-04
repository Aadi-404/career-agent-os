from app.models.analysis import (
    AnalyzeRequest,
    CrossQuestionChain,
    PreparationDay,
    PreparationIntelligence,
    PriorityTopic,
    ResearchContextNote,
    RequirementMatch,
    ScoreBreakdownItem,
)


def build_preparation_intelligence(
    request: AnalyzeRequest,
    requirement_matches: list[RequirementMatch],
    score_breakdown: list[ScoreBreakdownItem],
    research_notes: list[ResearchContextNote] | None = None,
) -> PreparationIntelligence:
    research_notes = research_notes or []
    priority_topics = _research_priority_topics(research_notes) + _priority_topics(request, requirement_matches, score_breakdown)
    priority_topics = _dedupe_priority_topics(priority_topics)
    daily_plan = _daily_plan(request.preparationPlanDays, priority_topics)
    cross_question_chains = _cross_question_chains(request, priority_topics, requirement_matches)
    return PreparationIntelligence(
        summary=_summary(priority_topics, request.preparationPlanDays, research_notes),
        priorityTopics=priority_topics,
        dailyPlan=daily_plan,
        crossQuestionChains=cross_question_chains,
        phase5ResearchBacklog=_research_backlog(research_notes),
    )


def _research_priority_topics(research_notes: list[ResearchContextNote]) -> list[PriorityTopic]:
    topics: list[PriorityTopic] = []
    for note in research_notes[:8]:
        source = note.company or note.roleTitle or note.title
        for topic in note.preparationTopics[:4]:
            topics.append(
                PriorityTopic(
                    topic=_clean_topic(topic),
                    priority="high",
                    sourceRequirement=f"Research note: {note.title}",
                    reason=f"Saved {note.researchType} research for {source} highlights this as interview preparation.",
                    currentEvidence=note.summary[:240],
                    targetDepth="Prepare a company/role-specific answer with project proof, tradeoffs, and follow-up handling.",
                    actions=[
                        "Connect this topic to one resume project or work example.",
                        "Prepare one likely follow-up question from the research signal.",
                        "Write an honest gap answer if the resume does not prove it yet.",
                    ],
                )
            )
        for signal in note.keySignals[:3]:
            topics.append(
                PriorityTopic(
                    topic=_clean_topic(signal),
                    priority="medium",
                    sourceRequirement=f"Research signal: {note.title}",
                    reason=f"Saved research signal from {source}.",
                    currentEvidence=note.summary[:240],
                    targetDepth="Be ready to explain why this signal matters for the target role and how your experience maps to it.",
                    actions=["Prepare one concise explanation.", "Map it to resume evidence.", "Prepare one cross-question."],
                )
            )
    return topics[:10]


def _priority_topics(
    request: AnalyzeRequest,
    requirement_matches: list[RequirementMatch],
    score_breakdown: list[ScoreBreakdownItem],
) -> list[PriorityTopic]:
    weak_or_missing = sorted(
        requirement_matches,
        key=lambda match: (_importance_rank(match.importance), match.score),
    )
    topics: list[PriorityTopic] = []
    for match in weak_or_missing:
        if match.score >= 70 and match.importance != "high":
            continue
        priority = _priority(match)
        topics.append(
            PriorityTopic(
                topic=_clean_topic(match.requirement),
                priority=priority,
                sourceRequirement=match.requirement,
                reason=_priority_reason(match),
                currentEvidence=match.bestEvidence,
                targetDepth=_target_depth(request.candidateContext.experienceYears, match),
                actions=_topic_actions(match),
            )
        )

    if topics:
        return topics[:8]

    weakest_breakdowns = sorted(score_breakdown, key=lambda item: item.score)[:3]
    return [
        PriorityTopic(
            topic=_clean_topic(item.category),
            priority="medium",
            sourceRequirement=item.category,
            reason=item.reason,
            currentEvidence=None,
            targetDepth=_experience_depth(request.candidateContext.experienceYears),
            actions=[
                "Prepare one practical explanation.",
                "Map the topic to one project or work example.",
                "Prepare one tradeoff and one failure/debugging example.",
            ],
        )
        for item in weakest_breakdowns
    ]


def _daily_plan(days: int, topics: list[PriorityTopic]) -> list[PreparationDay]:
    if not topics:
        topics = [
            PriorityTopic(
                topic="Role-specific project explanation",
                priority="medium",
                sourceRequirement="General preparation",
                reason="No weak requirement was detected, so preparation focuses on articulation and proof depth.",
                currentEvidence=None,
                targetDepth="Explain one project end to end with tradeoffs, tests, deployment, and measurable result.",
                actions=["Prepare a project story.", "Practice cross-questions.", "Revise the final resume evidence."],
            )
        ]

    plan: list[PreparationDay] = []
    templates = [
        ("Gap map", "Convert weak JD requirements into a focused prep backlog."),
        ("Concept depth", "Understand the highest-priority missing or weak topic."),
        ("Hands-on proof", "Create or revise a practical example for the topic."),
        ("Project story", "Connect the topic to a real project explanation."),
        ("Cross-question drill", "Practice follow-up questions under interview pressure."),
        ("System thinking", "Prepare design, reliability, scale, and tradeoff angles."),
        ("Final mock", "Run a full mock answer pass and update resume evidence."),
    ]

    for index in range(days):
        topic = topics[index % len(topics)]
        focus, goal = templates[index] if index < len(templates) else ("Revision loop", "Repeat weak-topic practice and tighten answers.")
        plan.append(
            PreparationDay(
                day=index + 1,
                focus=f"{focus}: {topic.topic}",
                goal=goal,
                tasks=_day_tasks(index, topic),
                output=_day_output(index, topic),
            )
        )
    return plan


def _cross_question_chains(
    request: AnalyzeRequest,
    topics: list[PriorityTopic],
    requirement_matches: list[RequirementMatch],
) -> list[CrossQuestionChain]:
    selected = topics[:6]
    if not selected:
        selected = [
            PriorityTopic(
                topic=request.candidateContext.targetRole,
                priority="medium",
                sourceRequirement=request.candidateContext.targetRole,
                reason="General role preparation.",
                currentEvidence=None,
                targetDepth=_experience_depth(request.candidateContext.experienceYears),
                actions=[],
            )
        ]

    matches_by_requirement = {match.requirement: match for match in requirement_matches}
    chains = []
    for topic in selected:
        match = matches_by_requirement.get(topic.sourceRequirement)
        chains.append(
            CrossQuestionChain(
                topic=topic.topic,
                openingQuestion=f"Explain your hands-on experience with {topic.topic}.",
                followUps=_follow_ups(topic, match),
                expectedAnswerFocus=(
                    "Answer with project context, your exact responsibility, implementation details, "
                    "tradeoffs, testing/debugging, and result."
                ),
                risk=_risk(topic, match),
            )
        )
    return chains


def _summary(topics: list[PriorityTopic], days: int, research_notes: list[ResearchContextNote]) -> str:
    if not topics:
        return f"Preparation plan is set for {days} day(s). No major weak requirement was detected, so focus on project explanation depth."
    critical = sum(1 for topic in topics if topic.priority == "critical")
    high = sum(1 for topic in topics if topic.priority == "high")
    research_part = f" It includes {len(research_notes)} saved research note(s)." if research_notes else ""
    return f"Preparation plan is set for {days} day(s), prioritizing {critical} critical and {high} high-priority topic(s) from the JD match matrix and research memory.{research_part}"


def _research_backlog(research_notes: list[ResearchContextNote]) -> list[str]:
    if research_notes:
        return [
            "Add cited web sources to validate the saved manual research signals.",
            "Compare this role with similar recent job posts before final application prioritization.",
        ]
    return [
        "Research similar job interview questions from recent web sources.",
        "Research company-specific interview experiences and frequently asked topics.",
    ]


def _dedupe_priority_topics(topics: list[PriorityTopic]) -> list[PriorityTopic]:
    seen: set[str] = set()
    deduped: list[PriorityTopic] = []
    for topic in topics:
        key = _clean_topic(topic.topic).lower()
        if key in seen:
            continue
        seen.add(key)
        deduped.append(topic)
    return deduped[:10]


def _priority(match: RequirementMatch) -> str:
    if match.importance == "high" and match.score < 45:
        return "critical"
    if match.importance == "high" or match.score < 35:
        return "high"
    if match.score < 60:
        return "medium"
    return "low"


def _priority_reason(match: RequirementMatch) -> str:
    if match.score == 0:
        return f"The JD requirement is {match.importance} importance and no matching resume evidence was found."
    if match.score < 55:
        return f"The JD requirement is only weakly supported. Current match type: {match.matchType}. {match.reason}"
    return f"The JD requirement has evidence, but it is important enough to rehearse deeply. Current match type: {match.matchType}."


def _target_depth(experience_years: float, match: RequirementMatch) -> str:
    base = _experience_depth(experience_years)
    if match.importance == "high":
        return f"{base} Be ready for implementation, tradeoffs, debugging, and project proof."
    return base


def _experience_depth(experience_years: float) -> str:
    if experience_years < 2:
        return "Know fundamentals, small implementation examples, and common interview definitions."
    if experience_years <= 4:
        return "Know practical implementation, project usage, debugging, testing, and tradeoffs."
    return "Know design decisions, ownership, scaling, reliability, mentoring, and business impact."


def _topic_actions(match: RequirementMatch) -> list[str]:
    actions = [
        "Prepare a concise concept explanation.",
        "Map it to one resume project or honestly mark it as a learning gap.",
        "Prepare one practical example and one tradeoff.",
    ]
    if match.score < 55:
        actions.append("Add or rewrite a truthful resume bullet if you have real evidence.")
    if match.evidenceSource == "certification":
        actions.append("Separate certification knowledge from hands-on project experience in your answer.")
    return actions


def _day_tasks(index: int, topic: PriorityTopic) -> list[str]:
    if index == 0:
        return [
            f"Review why '{topic.topic}' is a priority.",
            "Write whether you have real project evidence, certification evidence, or only learning exposure.",
            "List the exact resume/JD lines connected to this topic.",
        ]
    if index == 1:
        return [
            f"Revise fundamentals for {topic.topic}.",
            "Write a 90-second interview explanation.",
            "Prepare one example, one edge case, and one limitation.",
        ]
    if index == 2:
        return [
            f"Create or revise a small hands-on example for {topic.topic}.",
            "Note implementation steps, tools used, and failure points.",
            "Write what you would say if asked for proof.",
        ]
    if index == 3:
        return [
            "Convert the topic into a STAR project story.",
            "Cover situation, task, action, result, and exact ownership.",
            "Add metrics or operational impact if truthful.",
        ]
    if index == 4:
        return [
            "Answer the cross-question chain aloud.",
            "Record weak answers.",
            "Rewrite answers to be specific and honest.",
        ]
    if index == 5:
        return [
            "Prepare system design angles connected to the topic.",
            "Cover API/data flow, scaling, reliability, security, and observability.",
            "Identify one tradeoff you can defend.",
        ]
    return [
        "Run a timed mock interview pass.",
        "Update resume evidence for weak answers.",
        "Revise the next highest-priority topic.",
    ]


def _day_output(index: int, topic: PriorityTopic) -> str:
    outputs = [
        "A written gap map.",
        "A 90-second concept explanation.",
        "A small implementation/proof note.",
        "A STAR project story.",
        "Answered cross-question chain.",
        "A system-design/tradeoff note.",
        "Final mock notes and resume edits.",
    ]
    return f"{outputs[index] if index < len(outputs) else 'Updated revision notes'} for {topic.topic}."


def _follow_ups(topic: PriorityTopic, match: RequirementMatch | None) -> list[str]:
    evidence_question = (
        "Which exact project or work item proves this?"
        if match and match.bestEvidence
        else "If this is not in your resume, how will you honestly explain the gap?"
    )
    return [
        evidence_question,
        "What did you personally implement or debug?",
        "What tradeoff or limitation did you face?",
        "How did you test or validate it?",
        "What would you improve if you had to do it again?",
    ]


def _risk(topic: PriorityTopic, match: RequirementMatch | None) -> str:
    if match is None or match.score == 0:
        return "High risk: interviewer may see this as missing if the JD requires it."
    if match.score < 55:
        return "Medium risk: evidence exists but may sound shallow without a concrete project story."
    if match.evidenceSource in {"skills", "candidate_context"}:
        return "Medium risk: listed skill or context is weaker than project evidence."
    return "Low risk if you can explain the project details clearly."


def _importance_rank(importance: str) -> int:
    if importance == "high":
        return 0
    if importance == "medium":
        return 1
    return 2


def _clean_topic(value: str) -> str:
    cleaned = value.split(":", 1)[0].strip()
    return cleaned.replace("_", " ").replace("/", " / ")
