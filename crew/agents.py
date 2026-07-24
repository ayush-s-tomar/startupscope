from crewai import Agent, LLM
from tools.search_tool import search_the_internet
from dotenv import load_dotenv
import os

load_dotenv()


# ── Secrets helper ───────────────────────────────────────────────────────────
# Works both locally (.env via os.getenv) and on Streamlit Cloud (st.secrets).
def get_secret(key: str) -> str:
    try:
        import streamlit as st
        if key in st.secrets:
            return st.secrets[key]
    except Exception:
        pass
    return os.getenv(key, "")


# ── Shared structured context dict ─────────────────────────────────────────
agent_context: dict = {
    "company_name":         "",
    "product_summary":      "",
    "founded":              "",
    "hq":                   "",
    "team_size":            "",
    "funding": {
        "total_raised":     "",
        "last_round":       "",
        "investors":        []
    },
    "competitors":          [],
    "recent_news":          [],
    "tech_stack":           [],
    "growth_metrics":       "",
    "strengths":            [],
    "risks":                [],
    "market_opportunity":   "",
    "competitive_position": "",
    "verdict":              "",
    "what_they_do":         "",
    "business_model":       "",
    "verdict_rationale":    ""
}


def reset_context(company_name: str) -> None:
    """
    Call once before each crew run to wipe stale data.
    Also resets the Bundle 4 schema fields so the JSON export is always fresh.
    """
    global agent_context
    agent_context = {
        "company_name":         company_name,
        "product_summary":      "",
        "founded":              "",
        "hq":                   "",
        "team_size":            "",
        "funding": {
            "total_raised":     "",
            "last_round":       "",
            "investors":        []
        },
        "competitors":          [],
        "recent_news":          [],
        "tech_stack":           [],
        "growth_metrics":       "",
        "strengths":            [],
        "risks":                [],
        "market_opportunity":   "",
        "competitive_position": "",
        "verdict":              "",
        "what_they_do":         "",
        "business_model":       "",
        "verdict_rationale":    ""
    }


# ── LLM factory ────────────────────────────────────────────────────────────

def get_llm():
    return LLM(
        model="groq/llama-3.3-70b-versatile",
        api_key=get_secret("GROQ_API_KEY"),
        temperature=0.3
    )


# ── Agent factories ────────────────────────────────────────────────────────

def get_researcher():
    return Agent(
        role="Startup Research Specialist",
        goal=(
            "Find comprehensive, up-to-date information about the given startup. "
            "Gather data on their product, funding history, team, competitors, and "
            "recent news. Store every finding in the shared agent_context dict under "
            "the correct key (funding, competitors, recent_news, tech_stack, etc.) "
            "so downstream agents receive structured data, not raw prose. "
            "Also populate agent_context['what_they_do'] with a 2-3 sentence "
            "description of the product/service."
        ),
        backstory=(
            "You are an expert startup analyst who has spent 10 years researching "
            "tech companies for venture capital firms. You are meticulous about "
            "separating facts from speculation and always cite your sources."
        ),
        tools=[search_the_internet],
        llm=get_llm(),
        verbose=True,
        allow_delegation=False,
        max_iter=4,
        memory=True
    )


def get_analyst():
    return Agent(
        role="Business Intelligence Analyst",
        goal=(
            "Using the structured research in agent_context, extract the most "
            "important business insights. Populate: "
            "agent_context['strengths'] — list of 2-3 strength strings; "
            "agent_context['risks'] — list of 2-3 risk strings; "
            "agent_context['market_opportunity'] — 1-2 sentence TAM summary; "
            "agent_context['competitive_position'] — 1-2 sentence positioning; "
            "agent_context['verdict'] — exactly one of: 'Promising', 'Neutral', 'Risky'; "
            "agent_context['business_model'] — how the company makes money (2-3 sentences); "
            "agent_context['verdict_rationale'] — 2-3 sentence explanation of the verdict."
        ),
        backstory=(
            "You are a senior business analyst who has evaluated hundreds of startups "
            "for Series A/B investment decisions. You cut through noise and surface "
            "the 2-3 things that actually determine whether a company succeeds."
        ),
        llm=get_llm(),
        verbose=True,
        allow_delegation=False,
        max_iter=2,
        memory=True
    )


def get_writer():
    return Agent(
        role="Intelligence Report Writer",
        goal=(
            "Read the fully-populated agent_context dict and transform it into a "
            "clear, professional markdown intelligence report. Every section must be "
            "grounded in data from agent_context — do not invent figures. "
            "If a field in agent_context is empty, write 'Data unavailable' for that section. "
            "The report MUST follow this exact heading structure so the JSON exporter works: "
            "## Overview / ## Quick Facts / ## What They Do / ## Business Model / "
            "## Strengths / ## Risks / ## Competitive Landscape / ## Recent News / ## Verdict"
        ),
        backstory=(
            "You are a technical writer who specialises in investment memos and company "
            "briefs. You write for busy founders and investors who need facts fast."
        ),
        llm=get_llm(),
        verbose=True,
        allow_delegation=False,
        max_iter=2,
        memory=True
    )
