from crewai import Task
from crew.agents import agent_context


# ── Helper ─────────────────────────────────────────────────────────────────

def _context_snapshot() -> str:
    """Return a human-readable summary of what agent_context currently holds."""
    import json
    return json.dumps(agent_context, indent=2, ensure_ascii=False)


# ── Task factories ──────────────────────────────────────────────────────────

def get_research_task(agent, company_name: str):
    """
    Parallel task 1 — runs at the same time as the analysis task.
    The researcher populates agent_context with raw, typed findings.
    """
    return Task(
        description=f"""
Research the company: **{company_name}**.

Run at least 4 different web searches using varied query angles, for example:
  - "{company_name} startup funding history investors"
  - "{company_name} product features business model revenue"
  - "{company_name} competitors market"
  - "{company_name} news 2024 2025"

For every finding, write the value into the shared agent_context dict:

  agent_context["product_summary"]        — one sentence: what the company does
  agent_context["founded"]                — year founded (string)
  agent_context["hq"]                     — city, country
  agent_context["team_size"]              — approximate headcount
  agent_context["funding"]["total_raised"]— e.g. "$120M"
  agent_context["funding"]["last_round"]  — e.g. "Series B, Jan 2024"
  agent_context["funding"]["investors"]   — list of investor name strings
  agent_context["competitors"]            — list of dicts:
                                            [{{"name": "...", "model": "...", "funding": "..."}}]
                                            (minimum 3 competitors)
  agent_context["recent_news"]            — list of dicts:
                                            [{{"headline": "...", "date": "...", "source": "..."}}]
                                            (minimum 3 news items from last 6 months)
  agent_context["tech_stack"]             — list of technology/product feature strings
  agent_context["growth_metrics"]         — any public revenue or growth figure

If a field cannot be found after two searches, set it to "Not publicly available".
Do NOT leave any field empty — always write a value.
        """,
        agent=agent,
        expected_output=(
            "A confirmation that agent_context has been fully populated, followed by "
            "a JSON dump of agent_context showing all fields filled in. "
            "Competitors list must have at least 3 entries. "
            "recent_news list must have at least 3 entries."
        )
    )


def get_analysis_task(agent, company_name: str):
    """
    Parallel task 2 — runs at the same time as the research task.
    The analyst reads agent_context (populated by researcher) and writes
    its own insights back into the same shared dict.
    """
    return Task(
        description=f"""
Analyse the structured research data for **{company_name}** from agent_context.

Current context snapshot:
{_context_snapshot()}

Your job is to read the above and write the following fields back into agent_context:

  agent_context["strengths"]              — list of 2-3 concise strength strings
  agent_context["risks"]                  — list of 2-3 concise risk strings
  agent_context["market_opportunity"]     — 1-2 sentence market sizing / TAM summary
  agent_context["competitive_position"]   — 1-2 sentence summary of how the company
                                            stands vs. its competitors
  agent_context["verdict"]                — MUST be exactly one of:
                                            "Promising" | "Neutral" | "Risky"

Rules:
- Base every insight on data already in agent_context. Do not invent figures.
- Strengths and risks must be specific (e.g. "Strong Series B backing from Tiger Global"
  not "Has good investors").
- Verdict should reflect the balance of strengths vs. risks vs. market timing.
        """,
        agent=agent,
        expected_output=(
            "A confirmation that agent_context has been updated with strengths, risks, "
            "market_opportunity, competitive_position, and verdict. "
            "Followed by a JSON dump of only those five fields showing the new values. "
            "Verdict must be exactly 'Promising', 'Neutral', or 'Risky'."
        )
    )


def get_writing_task(agent, company_name: str):
    """
    Sequential task — runs AFTER both parallel tasks complete.
    The writer reads the fully-populated agent_context and renders the report.
    """
    return Task(
        description=f"""
Write the final intelligence report for **{company_name}** using the data in agent_context.

Current context (fully populated):
{_context_snapshot()}

Render the report in this exact markdown format:

---
# {company_name} — Intelligence Report

## Overview
(1-2 sentences from agent_context["product_summary"] and agent_context["market_opportunity"])

## Quick Facts
| Field        | Value |
|--------------|-------|
| Founded      | {{agent_context["founded"]}} |
| HQ           | {{agent_context["hq"]}} |
| Team size    | {{agent_context["team_size"]}} |
| Total raised | {{agent_context["funding"]["total_raised"]}} |
| Last round   | {{agent_context["funding"]["last_round"]}} |

## What They Do
(Expand on agent_context["product_summary"] with tech_stack details)

## Business Model
(Infer how they monetise from the research data)

## Strengths
(Bullet list from agent_context["strengths"])

## Risks
(Bullet list from agent_context["risks"])

## Competitive Landscape
(Table or bullet list from agent_context["competitors"] + agent_context["competitive_position"])

## Recent News
(Bullet list from agent_context["recent_news"] — include date and source)

## Verdict
**{{agent_context["verdict"]}}**
(2-3 sentence rationale)

---
*Report generated by StartupScope*
---

Rules:
- Replace all {{...}} placeholders with real values from agent_context.
- If any agent_context field is empty or "Not publicly available", write exactly
  that in the report — never invent data.
- Keep the table in Quick Facts — do not replace it with prose.
        """,
        agent=agent,
        expected_output=(
            "A complete, formatted markdown intelligence report with all 9 sections "
            "populated from agent_context. No placeholder text like '{{company_name}}' "
            "should remain. The Quick Facts section must be a markdown table. "
            "Verdict must match agent_context['verdict'] exactly."
        )
    )
