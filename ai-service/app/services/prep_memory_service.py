from collections import defaultdict

from app.models.history import AnalysisRecord, PreparationSessionRecord
from app.models.prep_memory import PrepMemoryResponse, PrepMemoryTopic, PrepProgressMemory, PrepNextAction


def build_prep_memory(
    analyses: list[AnalysisRecord],
    preparation_sessions: list[PreparationSessionRecord],
) -> PrepMemoryResponse:
    weak_topics = _weak_topic_memory(analyses)
    unfinished = _unfinished_progress_memory(preparation_sessions)
    actions = _recommended_actions(weak_topics, unfinished)
    next_action = _next_action(weak_topics, preparation_sessions, unfinished)
    summary = _summary(weak_topics, unfinished)
    return PrepMemoryResponse(
        summary=summary,
        repeatedWeakTopics=weak_topics,
        unfinishedPreparation=unfinished,
        nextRecommendedActions=actions,
        nextAction=next_action,
    )


def _weak_topic_memory(analyses: list[AnalysisRecord]) -> list[PrepMemoryTopic]:
    grouped: dict[str, list[tuple[int, str | None]]] = defaultdict(list)
    for analysis in analyses:
        for match in analysis.response.requirementMatches:
            if match.score >= 60:
                continue
            key = _topic_key(match.requirement)
            grouped[key].append((match.score, match.bestEvidence or match.reason))

    topics = []
    for topic, scores in grouped.items():
        if len(scores) < 1:
            continue
        average = round(sum(score for score, _evidence in scores) / len(scores))
        latest_evidence = scores[0][1]
        topics.append(
            PrepMemoryTopic(
                topic=topic,
                occurrences=len(scores),
                averageScore=max(0, min(100, average)),
                latestEvidence=latest_evidence,
                recommendation=_topic_recommendation(topic, len(scores), average),
            )
        )
    return sorted(topics, key=lambda item: (-item.occurrences, item.averageScore, item.topic))[:8]


def _unfinished_progress_memory(sessions: list[PreparationSessionRecord]) -> list[PrepProgressMemory]:
    progress_items = []
    for session in sessions:
        progress = session.progress or {}
        tasks = progress.get("tasks", {}) if isinstance(progress, dict) else {}
        confidence = progress.get("confidence", {}) if isinstance(progress, dict) else {}
        if not isinstance(tasks, dict):
            tasks = {}
        if not isinstance(confidence, dict):
            confidence = {}

        total = len(tasks)
        done = sum(1 for status in tasks.values() if status in {"done", "skipped"})
        if total == 0:
            total = _planned_task_count(session)
            done = total if session.status == "completed" else 0
        unfinished = max(0, total - done)
        completion = round((done / total) * 100) if total else 0
        low_confidence_days = sum(1 for value in confidence.values() if value == "low")
        if unfinished == 0 and low_confidence_days == 0:
            continue
        progress_items.append(
            PrepProgressMemory(
                sessionId=session.id,
                title=session.title,
                status=session.status,
                completionPercent=completion,
                unfinishedTaskCount=unfinished,
                lowConfidenceDays=low_confidence_days,
            )
        )
    return sorted(progress_items, key=lambda item: (item.completionPercent, -item.unfinishedTaskCount))[:6]


def _planned_task_count(session: PreparationSessionRecord) -> int:
    plan = session.plan
    daily_plan = plan.get("dailyPlan", []) if isinstance(plan, dict) else plan.dailyPlan
    if not isinstance(daily_plan, list):
        return 0
    total = 0
    for day in daily_plan:
        tasks = day.get("tasks", []) if isinstance(day, dict) else getattr(day, "tasks", [])
        total += len(tasks)
    return total


def _recommended_actions(weak_topics: list[PrepMemoryTopic], unfinished: list[PrepProgressMemory]) -> list[str]:
    actions = []
    if weak_topics:
        top = weak_topics[0]
        actions.append(f"Prioritize {top.topic}; it appears weak across {top.occurrences} saved analysis result(s).")
    if len(weak_topics) > 1:
        actions.append("Create one focused preparation block for the top repeated weak topics before analyzing more jobs.")
    if unfinished:
        session = unfinished[0]
        if session.unfinishedTaskCount > 0:
            actions.append(f"Resume '{session.title}' first; it still has {session.unfinishedTaskCount} unfinished task(s).")
        else:
            actions.append(f"Review confidence for '{session.title}' before starting a new preparation plan.")
    if not actions:
        actions.append("No repeated weak topic is visible yet. Analyze more JDs or complete a preparation session to build memory.")
    return actions[:4]


def _next_action(
    weak_topics: list[PrepMemoryTopic],
    sessions: list[PreparationSessionRecord],
    unfinished: list[PrepProgressMemory],
) -> PrepNextAction | None:
    if unfinished:
        session_lookup = {session.id: session for session in sessions}
        selected_memory = unfinished[0]
        selected_session = session_lookup.get(selected_memory.sessionId)
        if selected_session:
            task = _first_unfinished_task(selected_session)
            if task:
                return PrepNextAction(
                    kind="continue_preparation",
                    label=f"Continue {selected_session.title}",
                    sessionId=selected_session.id,
                    sessionTitle=selected_session.title,
                    day=task["day"],
                    taskId=task["taskId"],
                    task=task["task"],
                    reason=f"Lowest-completion active preparation session has {selected_memory.unfinishedTaskCount} unfinished task(s).",
                )
            return PrepNextAction(
                kind="review_confidence",
                label=f"Review confidence for {selected_session.title}",
                sessionId=selected_session.id,
                sessionTitle=selected_session.title,
                reason="The session has low-confidence days even though no unfinished task was found.",
            )

    if weak_topics:
        top = weak_topics[0]
        return PrepNextAction(
            kind="prepare_repeated_gap",
            label=f"Prepare {top.topic}",
            task=top.topic,
            reason=f"This topic is weak across {top.occurrences} saved analysis result(s).",
        )

    return None


def _first_unfinished_task(session: PreparationSessionRecord) -> dict[str, int | str] | None:
    progress = session.progress or {}
    task_statuses = progress.get("tasks", {}) if isinstance(progress, dict) else {}
    if not isinstance(task_statuses, dict):
        task_statuses = {}

    for day in _daily_plan_items(session):
        day_number = _day_value(day)
        tasks = _tasks_value(day)
        for index, task in enumerate(tasks):
            task_id = f"day-{day_number}-task-{index}"
            status = task_statuses.get(task_id, "todo")
            if status not in {"done", "skipped"}:
                return {"day": day_number, "taskId": task_id, "task": str(task)}
    return None


def _daily_plan_items(session: PreparationSessionRecord) -> list:
    plan = session.plan
    daily_plan = plan.get("dailyPlan", []) if isinstance(plan, dict) else plan.dailyPlan
    return daily_plan if isinstance(daily_plan, list) else []


def _day_value(day: object) -> int:
    if isinstance(day, dict):
        value = day.get("day", 1)
    else:
        value = getattr(day, "day", 1)
    try:
        return max(1, min(30, int(value)))
    except (TypeError, ValueError):
        return 1


def _tasks_value(day: object) -> list:
    tasks = day.get("tasks", []) if isinstance(day, dict) else getattr(day, "tasks", [])
    return tasks if isinstance(tasks, list) else []


def _summary(weak_topics: list[PrepMemoryTopic], unfinished: list[PrepProgressMemory]) -> str:
    if weak_topics and unfinished:
        return f"Found {len(weak_topics)} repeated weak topic(s) and {len(unfinished)} preparation session(s) needing follow-up."
    if weak_topics:
        return f"Found {len(weak_topics)} repeated weak topic(s) from saved match history."
    if unfinished:
        return f"Found {len(unfinished)} preparation session(s) with unfinished work or low confidence."
    return "No strong prep memory signal yet. Keep saving analyses and tracking preparation progress."


def _topic_recommendation(topic: str, occurrences: int, average_score: int) -> str:
    if occurrences >= 3:
        return f"Treat {topic} as a recurring gap. Prepare concept, implementation, and one resume-backed example."
    if average_score < 35:
        return f"Build fundamentals for {topic}, then add honest project or learning evidence."
    return f"Strengthen proof depth for {topic}; current evidence is present but not convincing enough."


def _topic_key(value: str) -> str:
    return " ".join(value.strip().split())
