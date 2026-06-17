# Career Agent OS Roadmap

## Goal

Career Agent OS is not only a resume analyzer. The goal is to become a career decision and interview preparation system for job switching, especially for fullstack and AI-oriented developers in the Indian market.

The app should answer practical questions:

- Should I apply to this role?
- Why is my resume a strong or weak fit?
- What topics should I prepare for this company and role?
- What shortlisting factors can reduce my chances?
- How should I rewrite my resume without inventing experience?
- What interview cross-questions should I expect?

## Core Design Principle

The scoring should not depend only on the LLM.

Use this split:

```text
Algorithm calculates.
LLM explains and coaches.
```

Why:

- LLM scores can be inconsistent.
- Algorithmic scoring is easier to debug.
- Score breakdowns are easier to explain in interviews.
- Future research and embedding layers can plug into the same contract.

## Current Level 1

Level 1 is the resume and JD technical fit analyzer.

It already supports:

- Resume text input
- Resume upload for TXT, PDF, DOCX
- Mock and live LLM modes
- Groq, OpenAI, and Gemini provider selection
- Technical match score
- Matching skills
- Weakly evidenced skills
- Missing skills
- Resume improvements
- Interview questions
- Cross-questions
- System design readiness
- 7-day preparation plan

## Level 1.5: Resume Normalization and Explainable Scoring

### Problem

Raw PDF/DOCX extraction can produce noisy text:

```text
Used
ASP.NET Core, EF, and Angular
Used
SQL Server
Implemented
CRUD operations
```

This is poor input for analysis because sections and bullet relationships are unclear.

### Flow

```text
Upload resume
-> Extract raw text
-> Normalize resume
-> User reviews/edits normalized text
-> Parse JD
-> User reviews/edits normalized JD text
-> Analyze against JD
```

### Resume Normalization Output

The backend creates:

- Profile
- Experience
- Projects
- Skills
- Education
- Achievements
- Certifications
- Warnings

Example:

```json
{
  "profile": {
    "name": "Aditya Rana",
    "location": "Navi Mumbai",
    "summary": "Full-stack .NET developer with ASP.NET Core, C#, SQL Server, Angular and production support experience."
  },
  "experience": [],
  "projects": [],
  "skills": [".NET", "ASP.NET", "C#", "SQL", "Angular"],
  "warnings": ["Projects section was not confidently detected."]
}
```

### Explainable Scoring Layers

The technical score is split into multiple scored categories.

For a 0-1 year candidate, the app gives more importance to:

- DSA and coding
- Core skills
- Projects
- Fullstack basics
- Database basics

For a 2-4 year candidate, the app gives more importance to:

- Project ownership
- Backend/frontend depth
- Database depth
- Production debugging
- Cloud/DevOps basics
- System design basics

For a 5+ year candidate, the app gives more importance to:

- Architecture
- System design
- Scalability and reliability
- Team ownership
- Cloud/DevOps
- Domain depth

### Score Breakdown Example

```json
{
  "technicalMatchScore": 64,
  "scoreBreakdown": [
    {
      "category": "experienceFit",
      "weight": 10,
      "score": 57,
      "weightedScore": 5.7,
      "reason": "JD expects at least 2 years; candidate has 1 year."
    },
    {
      "category": "coreSkills",
      "weight": 20,
      "score": 75,
      "weightedScore": 15,
      "reason": "Matched extracted JD skills: ASP.NET Core, C#, SQL."
    }
  ]
}
```

## Level 2: Shortlisting and Opportunity Scoring

Technical fit is not the same as shortlisting chance.

Level 2 adds hiring practicality signals:

- Location fit
- Preferred locations
- Notice period
- Work mode preference
- Relocation openness
- Current CTC
- Expected CTC
- Experience range fit

Protected attributes such as gender must not affect scoring.

### Level 2 Scores

The app now separates:

- `technicalMatchScore`
- `shortlistingScore`
- `interviewReadinessScore`
- `overallOpportunityScore`

Example formula:

```text
overallOpportunityScore =
technicalMatchScore * 0.45
+ shortlistingScore * 0.30
+ interviewReadinessScore * 0.25
```

### Shortlisting Factor Example

```json
{
  "factor": "Notice period",
  "impact": "neutral",
  "reason": "60-day notice is common but weaker than immediate or 30-day availability."
}
```

## Current Implementation Slice

This slice adds:

- `POST /ai/resume/normalize`
- `POST /ai/jd/parse`
- Structured resume normalization models
- Structured JD parsing models
- Experience-wise technical scoring weights
- Score breakdown response fields
- Requirement match matrix for JD requirement to resume evidence mapping
- Shortlisting score response fields
- Opportunity score response fields
- Frontend shortlisting inputs
- Frontend normalized resume review button
- Frontend parsed JD review button and extracted requirement summary
- Dynamic preparation plan length input, defaulting to 7 days
- Frontend score breakdown and shortlisting factor panels

## Future Level 2.5: Research-Grounded Company and Role Insights

This should not be mixed directly into the current analyzer yet.

Future research agent responsibilities:

- Search similar job posts
- Search company interview experiences
- Search role-specific topic patterns
- Search market demand signals
- Build company-specific topic preferences
- Cite sources used for weighting

Example:

```text
Adobe Software Engineer
-> DSA high priority
-> Operating Systems high priority
-> Concurrency and memory concepts medium-high priority
```

For .NET enterprise roles:

```text
ASP.NET Core
SQL Server
Entity Framework
Azure DevOps
REST APIs
Production debugging
```

## Future Level 3: Market Opportunity Score

Market opportunity should use recent web/research signals:

- Similar job posting frequency
- Role demand by location
- Skill demand trend
- Experience band demand
- Company hiring activity
- Salary/CTC trend if available

This should produce:

- `marketOpportunityScore`
- `trend`
- `signals`
- `sources`

## Interview Explanation Points

### Why not use only LLM scoring?

LLM scoring is opaque and can be inconsistent. The app uses deterministic scoring categories and lets the LLM explain, coach, and generate preparation guidance.

### Why not directly feed raw PDF text?

PDF and DOCX extraction can break layout. Normalization creates structured sections and lets the user review the resume before analysis.

### Why combine lexical, semantic, and structured scoring?

Lexical matching catches hard requirements. Semantic matching catches meaning and synonyms. Structured rules handle years, location, notice period, and CTC better than free-form LLM reasoning.

### Why exclude gender from scoring?

Gender is a protected attribute. It should not influence technical fit, shortlisting score, or opportunity score.
