# ── Prompt builders ─────────────────────────────────────────────────────────
#
# These return plain strings, not CrewAI Task objects. Each one is fed into
# a single flat call_llm() call in crew.py -- no agent loop, no tool-calling
# inside the LLM call itself. Search happens separately in Python (see
# crew.py's _run_searches), and its raw text results are pasted directly
# into the research prompt below.

RESEARCH_SYSTEM = (
    "You are an expert startup analyst. You are meticulous about separating "
    "facts from speculation and always return clean, valid JSON, never prose. "
    "You never conflate an investor relationship with an infrastructure or "
    "technology partnership -- those are different things and you keep them "
    "distinct. Only include a fact if it is explicitly present in the search "
    "results you were given -- do not infer cloud/infra partners, tech stack, "
    "or API compatibility from indirect context (e.g. an investor is not "
    "automatically an infra partner). Never state a company's cloud provider, "
    "hosting setup, or infrastructure architecture (e.g. 'multi-cloud', "
    "'built on AWS/Azure/GCP') unless a source explicitly says so in those "
    "terms -- these are easy to sound plausible about and easy to get wrong, "
    "so the default is to omit them entirely, not to describe them "
    "generically. Never state a funding total unless a source explicitly "
    "labels it as the cumulative/total amount raised -- a valuation figure "
    "or a single round's size is NOT the same thing as total funding raised, "
    "and conflating them is a factual error even if the numbers are 'close'."
)

ANALYSIS_SYSTEM = (
    "You are a senior business analyst evaluating startups for Series A/B "
    "investment decisions. Base every insight strictly on the data you are "
    "given, never invent figures or use outside knowledge. You never confuse "
    "an investor relationship with a technical or infrastructure partnership. "
    "Never introduce a cloud provider, hosting setup, or infrastructure "
    "architecture claim (e.g. 'multi-cloud', 'built on AWS/Azure/GCP') that "
    "isn't explicitly present in the research JSON you were given -- if "
    "tech_stack is empty or vague, leave infrastructure claims out entirely "
    "rather than describing a plausible-sounding generic setup. Never state "
    "a total funding figure that isn't explicitly present as total_raised in "
    "the data -- do not substitute a valuation or a single round's size."
)

WRITER_SYSTEM = (
    "You are a technical writer producing investment memos. You never pad a "
    "report with information you weren't given, especially technical claims "
    "about infrastructure or APIs that could be factually wrong. You render "
    "ONLY the fields present in the JSON you were given -- you do not add "
    "descriptive infrastructure language (cloud providers, hosting, 'scalable "
    "systems', 'multi-cloud', etc.) that isn't a literal field value, even if "
    "it would make the report sound more complete. If tech_stack is empty, "
    "you say so plainly rather than writing generic filler about it."
)


def build_research_prompt(company_name, search_results_text):
    return f"""
Company: {company_name}

Raw web search results below. Extract facts ONLY from this text -- do not
use outside knowledge.

--- SEARCH RESULTS ---
{search_results_text}
--- END SEARCH RESULTS ---

Output ONLY valid JSON, no prose, no markdown fences, with exactly these keys:
company_name, product_summary, founded, hq, team_size,
funding {{total_raised, last_round, investors[]}} -- total_raised is the
CUMULATIVE amount raised across all rounds to date (often phrased as
"has raised $X total" or reflected in a valuation figure); last_round is
just the size/name of the most recent round. These are usually different
numbers -- do not copy last_round's amount into total_raised unless a
source explicitly states it as the cumulative total.
competitors[] (each: name, model, funding — up to 3),
recent_news[] (each: headline, date, source — up to 3),
tech_stack[], growth_metrics.

If a field isn't in the search results, use "Not publicly available" (or []
for lists) — never omit a key.
    """


def build_analysis_prompt(company_name, research_json_text):
    return f"""
Company: {company_name}

Research data (JSON) below:

{research_json_text}

Return a NEW JSON object with all original fields unchanged, plus:
strengths[] (2, specific), risks[] (2, specific), market_opportunity
(1-2 sentences), competitive_position (1-2 sentences vs. competitors[]),
business_model (2-3 sentences), verdict ("Promising"|"Neutral"|"Risky"),
verdict_rationale (2-3 sentences).

Base every insight strictly on the data above. If a source field is
"Not publicly available" or empty, reflect that honestly rather than
guessing. Do not state or imply any cloud provider, infrastructure
partnership, or API compatibility claim unless it appears explicitly in the
data above.

Output ONLY the JSON object, no prose, no fences.
    """


def build_writing_prompt(company_name, analysis_json_text):
    return f"""
Company: {company_name}

Enriched data (JSON) below:

{analysis_json_text}

Render this exact markdown structure, filling every placeholder with real
values from the JSON:

# {company_name} — Intelligence Report

## Overview
(from product_summary + market_opportunity)

## Quick Facts
| Field | Value |
|---|---|
| Founded | founded |
| HQ | hq |
| Team size | team_size |
| Total raised | funding.total_raised |
| Last round | funding.last_round |

## What They Do
(expand product_summary using tech_stack -- ONLY if tech_stack has real
entries; if tech_stack is empty or "Not publicly available", describe what
the product does from product_summary alone and do not add any invented
infrastructure, cloud, or architecture detail to fill the gap)

## Business Model
(business_model)

## Strengths
(bullets from strengths)

## Risks
(bullets from risks)

## Competitive Landscape
(from competitors + competitive_position)

## Recent News
(bullets from recent_news, with date + source)

## Verdict
**verdict**
(verdict_rationale)

*Report generated by StartupScope*

Rules: use only actual JSON values, never invent data. If a field is
missing/empty/"Not publicly available", write "Data unavailable" for that
part. Keep Quick Facts as a markdown table.
    """