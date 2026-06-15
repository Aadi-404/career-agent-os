from app.models.analysis import AnalyzeRequest


def build_analysis_prompt(request: AnalyzeRequest) -> str:
    context = request.candidateContext
    stack = ", ".join(context.currentStack)

    return f"""
You are a senior technical interviewer and career coach.

Analyze the candidate resume against the job description.

Candidate profile:
- Target role: {context.targetRole}
- Experience: {context.experienceYears} years
- Current stack: {stack}
- Target market: {context.targetMarket}
- Preparation plan length: {request.preparationPlanDays} days

Important instructions:
- Be practical and interview-focused.
- Do not give generic advice.
- Focus only on technical fit, project depth, backend/frontend clarity, system design readiness, and likely interviewer cross-questions.
- Do not consider notice period, location, salary, or joining availability in this analysis.
- Judge the candidate according to their experience level, target role, and target market.
- Use the Resume as the primary evidence source.
- Use Candidate Context only to clarify background.
- If a skill appears in Candidate Context but not in Resume, mark it as weakly evidenced.
- Return only valid JSON.
- Do not include markdown.
- Do not include explanations outside JSON.

Resume:
{request.resumeText}

Job Description:
{request.jobDescriptionText}

Return JSON using this exact structure:

{{
  "technicalMatchScore": number,
  "overallSummary": string,
  "fitCategory": "Strong Fit" | "Good Fit" | "Partial Fit" | "Weak Fit",
  "matchingSkills": [
    {{
      "skill": string,
      "evidenceFromResume": string,
      "jdRequirement": string
    }}
  ],
  "weaklyEvidencedSkills": [
    {{
      "skill": string,
      "source": string,
      "whyWeak": string,
      "howToStrengthenResume": string
    }}
  ],
  "missingSkills": [
    {{
      "skill": string,
      "importance": "high" | "medium" | "low",
      "whyItMatters": string,
      "howToPrepare": string
    }}
  ],
  "resumeImprovements": [
    {{
      "currentIssue": string,
      "suggestedBullet": string,
      "reason": string
    }}
  ],
  "interviewQuestions": [
    {{
      "topic": string,
      "question": string,
      "difficulty": "easy" | "medium" | "hard",
      "expectedFocus": string
    }}
  ],
  "crossQuestions": [
    {{
      "question": string,
      "whyAsked": string,
      "expectedAnswerHint": string
    }}
  ],
  "systemDesignReadiness": {{
    "level": "strong" | "moderate" | "weak",
    "reason": string,
    "topicsToPrepare": [string]
  }},
  "sevenDayPlan": [
    {{
      "day": number,
      "focus": string,
      "tasks": [string]
    }}
  ]
}}

Rules:
- technicalMatchScore must be between 0 and 100.
- technicalMatchScore should be based mainly on Resume evidence against the JD.
- Do not reduce technicalMatchScore for notice period, location, salary, or joining availability.
- Give at least 5 matching skills if available.
- Give weaklyEvidencedSkills when a relevant skill is implied but not clearly proven in the resume.
- Give at least 5 missing or weak skills if available.
- Give at least 5 resume improvements.
- Give at least 8 interview questions.
- Give at least 8 cross-questions.
- sevenDayPlan must contain exactly {request.preparationPlanDays} day(s).
- day must start at 1 and end at {request.preparationPlanDays}.
- Keep the answer realistic for the candidate's experience level.
""".strip()
