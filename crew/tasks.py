from crewai import Task


# ── Task factories ──────────────────────────────────────────────────────────
#
# Each task's real output is data, not a side-effect. CrewAI passes a task's
# output text to any later task listed in that task's `.context` — that's the
# only reliable channel for handing data between agents.

def get_research_task(agent, company_name: str):
    """
    Task 1 — the Researcher runs searches and returns a single JSON object.
    This JSON becomes the task's output, which crew.py wires into the
    Analysis task's context.
    """
    return Task(
        description=f"""
Research the company: **{company_name}**.

Run at least 4 different web searches using varied query angles, for example:
  - "{company_name} startup funding history investors"
  - "{company_name} product features business model revenue"
  - "{company_name} competitors market"
  - "{company_name} news 2024 2025"

After researching, output ONLY a single valid JSON object with exactly this shape
(no prose before or after it, no markdown code fences):

{{
  "company_name": "{company_name}",
  "product_summary": "one sentence: what the company does",
  "founded": "year founded, or 'Not publicly available'",
  "hq": "city, country, or 'Not publicly available'",
  "team_size": "approximate headcount, or 'Not publicly available'",
  "funding": {{
    "total_raised": "e.g. '$120M', or 'Not publicly available'",
    "last_round": "e.g. 'Series B, Jan 2024', or 'Not publicly available'",
    "investors": ["list", "of", "investor names"]
  }},
  "competitors": [
    {{"name": "...", "model": "...", "funding": "..."}}
  ],
  "recent_news": [
    {{"headline": "...", "date": "...", "source": "..."}}
  ],
  "tech_stack": ["list", "of", "technology or product feature strings"],
  "growth_metrics": "any public revenue or growth figure, or 'Not publicly available'"
}}

Rules:
- competitors must have at least 3 entries when the data is available.
- recent_news must have at least 3 entries from the last 6 months when available.
- If a field truly cannot be found after searching, use "Not publicly available"
  (or an empty list for list fields) — never leave a field out of the JSON.
- Output must be valid JSON and nothing else.
        """,
        agent=agent,
        expected_output=(
            "A single valid JSON object with the exact keys described above, "
            "populated from real search results. No prose, no markdown fences, "
            "no commentary — JSON only."
        )
    )


def get_analysis_task(agent, company_name: str):
    """
    Task 2 — the Analyst receives the Researcher's JSON (via context) and
    returns an enriched JSON object with analysis fields added.
    """
    return Task(
        description=f"""
You will find the research data for **{company_name}** in your task context —
it is a JSON object produced by the previous task. Parse it.

Using only that data, produce a NEW JSON object that contains:
  - every field from the original research JSON, unchanged
  - plus these additional fields:
    "strengths":            list of 2-3 concise, specific strength strings
    "risks":                list of 2-3 concise, specific risk strings
    "market_opportunity":   1-2 sentence market sizing / TAM summary
    "competitive_position": 1-2 sentence summary of how the company stands
                             vs. its competitors (use the competitors list
                             from the research data)
    "business_model":       2-3 sentences on how the company makes money,
                             inferred from the research data
    "verdict":               exactly one of "Promising", "Neutral", "Risky"
    "verdict_rationale":     2-3 sentence explanation of the verdict

Rules:
- Base every insight strictly on the research data you were given. Do not
  invent figures or rely on outside/general knowledge.
- Strengths and risks must be specific (e.g. "Backed by a $110B round led by
  Amazon, Nvidia, and SoftBank" not "Has good investors").
- If the research data for a field is "Not publicly available" or empty,
  factor that into your analysis honestly rather than inventing a number.
- Output ONLY the JSON object — no prose, no markdown fences, no commentary.
        """,
        agent=agent,
        expected_output=(
            "A single valid JSON object containing all original research fields "
            "plus strengths, risks, market_opportunity, competitive_position, "
            "business_model, verdict, and verdict_rationale. JSON only."
        )
    )


def get_writing_task(agent, company_name: str):
    """
    Task 3 — the Writer receives the Analyst's fully-enriched JSON (via
    context) and renders the final markdown report.
    """
    return Task(
        description=f"""
You will find the fully-enriched JSON data for **{company_name}** in your task
context — it is the output of the previous (analysis) task. Parse it.

Render the report in this exact markdown format, replacing every placeholder
with a real value taken from the JSON:

---
# {company_name} — Intelligence Report

## Overview
(1-2 sentences from product_summary and market_opportunity)

## Quick Facts
| Field        | Value |
|--------------|-------|
| Founded      | founded |
| HQ           | hq |
| Team size    | team_size |
| Total raised | funding.total_raised |
| Last round   | funding.last_round |

## What They Do
(Expand on product_summary using tech_stack details)

## Business Model
(business_model)

## Strengths
(Bullet list from strengths)

## Risks
(Bullet list from risks)

## Competitive Landscape
(Table or bullet list from competitors, plus competitive_position)

## Recent News
(Bullet list from recent_news — include date and source for each)

## Verdict
**verdict**
(verdict_rationale)

---
*Report generated by StartupScope*
---

Rules:
- Use the ACTUAL values from the JSON you were given — never invent data.
- If a JSON field is missing, empty, "Not publicly available", or an empty
  list, write "Data unavailable" for that part of the report.
- Keep the Quick Facts table as a markdown table — do not replace it with prose.
        """,
        agent=agent,
        expected_output=(
            "A complete, formatted markdown intelligence report with all 9 sections "
            "populated from the JSON data you were given. No unresolved placeholders. "
            "The Quick Facts section must be a markdown table."
        )
    )