from collections import defaultdict
from datetime import datetime, timezone

from app.models.history import AnalysisRecord, PreparationSessionRecord
from app.models.prep_memory import (
    PrepAttentionSession,
    PrepMemoryResponse,
    PrepMemoryTopic,
    PrepProgressMemory,
    PrepNextAction,
    PrepTodayFocus,
)


def build_prep_memory(
    analyses: list[AnalysisRecord],
    preparation_sessions: list[PreparationSessionRecord],
    reference_time: datetime | None = None,
) -> PrepMemoryResponse:
    weak_topics = _weak_topic_memory(analyses)
    unfinished = _unfinished_progress_memory(preparation_sessions)
    schedule = _schedule_memory(preparation_sessions, reference_time or datetime.now(timezone.utc))
    actions = _recommended_actions(weak_topics, unfinished, schedule["today_focus"], schedule["attention_sessions"])
    next_action = _next_action(weak_topics, preparation_sessions, unfinished, schedule["today_focus"])
    summary = _summary(weak_topics, unfinished, schedule["today_focus"], schedule["attention_sessions"])
    return PrepMemoryResponse(
        summary=summary,
        repeatedWeakTopics=weak_topics,
        unfinishedPreparation=unfinished,
        todayFocus=schedule["today_focus"],
        attentionSessions=schedule["attention_sessions"],
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


def _schedule_memory(
    sessions: list[PreparationSessionRecord],
    reference_time: datetime,
) -> dict[str, list[PrepTodayFocus] | list[PrepAttentionSession]]:
    today_focus: list[PrepTodayFocus] = []
    attention_sessions: list[PrepAttentionSession] = []
    for session in sessions:
        if session.status == "completed":
            continue

        progress = session.progress or {}
        task_statuses = progress.get("tasks", {}) if isinstance(progress, dict) else {}
        confidence = progress.get("confidence", {}) if isinstance(progress, dict) else {}
        if not isinstance(task_statuses, dict):
            task_statuses = {}
        if not isinstance(confidence, dict):
            confidence = {}

        plan_days = _daily_plan_items(session)
        if not plan_days:
            continue

        current_day = _current_plan_day(session, reference_time, len(plan_days))
        overdue_count = 0
        first_unfinished: str | None = None
        session_focus: list[PrepTodayFocus] = []
        low_confidence_days = 0

        for day in plan_days:
            day_number = _day_value(day)
            day_key = f"day-{day_number}"
            day_confidence = str(confidence.get(day_key, "")) if confidence.get(day_key) else None
            if day_confidence == "low":
                low_confidence_days += 1

            for index, task in enumerate(_tasks_value(day)):
                task_id = f"{day_key}-task-{index}"
                status = str(task_statuses.get(task_id, "todo"))
                if status in {"done", "skipped"}:
                    continue

                task_text = str(task)
                first_unfinished = first_unfinished or task_text
                if day_number < current_day:
                    overdue_count += 1
                    session_focus.append(
                        PrepTodayFocus(
                            sessionId=session.id,
                            sessionTitle=session.title,
                            day=day_number,
                            taskId=task_id,
                            task=task_text,
                            status=status,
                            confidence=day_confidence,
                            urgency="overdue",
                            reason=f"Planned for day {day_number}, but this session is on day {current_day}.",
                        )
                    )
                elif day_number == current_day:
                    session_focus.append(
                        PrepTodayFocus(
                            sessionId=session.id,
                            sessionTitle=session.title,
                            day=day_number,
                            taskId=task_id,
                            task=task_text,
                            status=status,
                            confidence=day_confidence,
                            urgency="today",
                            reason="This task belongs to the current preparation day.",
                        )
                    )

        if not session_focus and low_confidence_days:
            low_day = _first_low_confidence_day(confidence)
            session_focus.append(
                PrepTodayFocus(
                    sessionId=session.id,
                    sessionTitle=session.title,
                    day=low_day,
                    task="Review notes and rerun practice for the low-confidence day.",
                    status="review",
                    confidence="low",
                    urgency="low_confidence",
                    reason="Confidence is low even though the task list has no current unfinished item.",
                )
            )

        if overdue_count or low_confidence_days:
            completion = _session_completion_percent(session)
            attention_sessions.append(
                PrepAttentionSession(
                    sessionId=session.id,
                    title=session.title,
                    currentPlanDay=current_day,
                    completionPercent=completion,
                    overdueTaskCount=overdue_count,
                    lowConfidenceDays=low_confidence_days,
                    nextTask=first_unfinished,
                    reason=_attention_reason(overdue_count, low_confidence_days),
                )
            )

        today_focus.extend(session_focus)

    return {
        "today_focus": sorted(today_focus, key=lambda item: (_urgency_rank(item.urgency), item.day, item.sessionTitle))[:8],
        "attention_sessions": sorted(
            attention_sessions,
            key=lambda item: (-item.overdueTaskCount, -item.lowConfidenceDays, item.completionPercent, item.title),
        )[:6],
    }


def _recommended_actions(
    weak_topics: list[PrepMemoryTopic],
    unfinished: list[PrepProgressMemory],
    today_focus: list[PrepTodayFocus],
    attention_sessions: list[PrepAttentionSession],
) -> list[str]:
    actions = []
    if today_focus:
        focus = today_focus[0]
        actions.append(f"Do '{focus.task}' from '{focus.sessionTitle}' first; urgency is {focus.urgency.replace('_', ' ')}.")
    if attention_sessions:
        attention = attention_sessions[0]
        actions.append(f"Recover '{attention.title}'; it has {attention.overdueTaskCount} overdue task(s) and {attention.lowConfidenceDays} low-confidence day(s).")
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
    today_focus: list[PrepTodayFocus],
) -> PrepNextAction | None:
    if today_focus:
        focus = today_focus[0]
        return PrepNextAction(
            kind="track_today_focus",
            label=f"{focus.urgency.replace('_', ' ').title()}: {focus.sessionTitle}",
            sessionId=focus.sessionId,
            sessionTitle=focus.sessionTitle,
            day=focus.day,
            taskId=focus.taskId,
            task=focus.task,
            reason=focus.reason,
        )

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


def _summary(
    weak_topics: list[PrepMemoryTopic],
    unfinished: list[PrepProgressMemory],
    today_focus: list[PrepTodayFocus],
    attention_sessions: list[PrepAttentionSession],
) -> str:
    if today_focus and attention_sessions:
        return f"Found {len(today_focus)} current preparation focus item(s), {len(attention_sessions)} session(s) needing attention, and {len(weak_topics)} repeated weak topic(s)."
    if today_focus:
        return f"Found {len(today_focus)} preparation focus item(s) for the current plan day."
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


def _current_plan_day(session: PreparationSessionRecord, reference_time: datetime, plan_day_count: int) -> int:
    created = _parse_datetime(session.createdAt) or reference_time
    elapsed_days = max(0, (reference_time.date() - created.date()).days)
    return max(1, min(max(1, plan_day_count), elapsed_days + 1, 30))


def _parse_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        normalized = value.replace("Z", "+00:00")
        parsed = datetime.fromisoformat(normalized)
        if parsed.tzinfo is None:
            return parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc)
    except ValueError:
        return None


def _session_completion_percent(session: PreparationSessionRecord) -> int:
    tasks = _all_task_ids(session)
    if not tasks:
        return 100 if session.status == "completed" else 0
    progress = session.progress or {}
    task_statuses = progress.get("tasks", {}) if isinstance(progress, dict) else {}
    if not isinstance(task_statuses, dict):
        task_statuses = {}
    completed = sum(1 for task_id in tasks if task_statuses.get(task_id) in {"done", "skipped"})
    return round((completed / len(tasks)) * 100)


def _all_task_ids(session: PreparationSessionRecord) -> list[str]:
    task_ids = []
    for day in _daily_plan_items(session):
        day_number = _day_value(day)
        for index, _task in enumerate(_tasks_value(day)):
            task_ids.append(f"day-{day_number}-task-{index}")
    return task_ids


def _first_low_confidence_day(confidence: dict) -> int:
    low_days = []
    for key, value in confidence.items():
        if value != "low" or not str(key).startswith("day-"):
            continue
        try:
            low_days.append(int(str(key).split("-", 1)[1]))
        except (IndexError, ValueError):
            continue
    return max(1, min(low_days or [1]))


def _attention_reason(overdue_count: int, low_confidence_days: int) -> str:
    if overdue_count and low_confidence_days:
        return "This plan has overdue work and low-confidence practice days."
    if overdue_count:
        return "This plan has tasks from earlier days that are still open."
    return "This plan has low-confidence days that should be reviewed before interview practice."


def _urgency_rank(value: str) -> int:
    return {"overdue": 0, "today": 1, "low_confidence": 2}.get(value, 3)
