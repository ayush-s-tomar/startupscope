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


# ── LLM factory ────────────────────────────────────────────────────────────

def get_llm():
    return LLM(
        model="groq/llama-3.3-70b-versatile",
        api_key=get_secret("GROQ_API_KEY"),
        temperature=0.3
    )


# ── Agent factories ────────────────────────────────────────────────────────
#
# NOTE: There is no shared "agent_context" dict anymore. LLM agents can only
# return text — they cannot mutate Python objects in this process just
# because a prompt tells them to. Instead, each agent's real output IS the
# data: the Researcher returns a JSON object, the Analyst reads that JSON
# (passed to it automatically by CrewAI via Task.context) and returns an
# enriched JSON object, and the Writer reads that JSON and renders markdown.

def get_researcher():
    """
    Searches the web and returns a single structured JSON object containing
    every researched fact. This JSON *is* the task's output — CrewAI will
    hand it to the next task automatically via task.context.
    """
    return Agent(
        role="Startup Research Specialist",
        goal=(
            "Find comprehensive, up-to-date information about the given startup "
            "by running multiple web searches, then output ONLY a single valid "
            "JSON object containing every finding. No prose, no markdown, no "
            "commentary before or after the JSON."
        ),
        backstory=(
            "You are an expert startup analyst who has spent 10 years researching "
            "tech companies for venture capital firms. You are meticulous about "
            "separating facts from speculation, and you always return clean, "
            "well-formed JSON — never prose."
        ),
        tools=[search_the_internet],
        llm=get_llm(),
        verbose=True,
        allow_delegation=False,
        max_iter=4,
        memory=True
    )


def get_analyst():
    """
    Receives the Researcher's JSON output (via Task.context) and returns an
    enriched JSON object: the original fields plus strengths, risks,
    market_opportunity, competitive_position, verdict, business_model, and
    verdict_rationale.
    """
    return Agent(
        role="Business Intelligence Analyst",
        goal=(
            "Read the JSON research data provided in your task context. Base every "
            "insight strictly on that data — never invent figures or fall back on "
            "general knowledge. Output ONLY a single valid JSON object: the "
            "original fields from the research data, plus your new analysis "
            "fields. No prose, no markdown, no commentary before or after the JSON."
        ),
        backstory=(
            "You are a senior business analyst who has evaluated hundreds of startups "
            "for Series A/B investment decisions. You cut through noise and surface "
            "the 2-3 things that actually determine whether a company succeeds. You "
            "never write generic filler — every claim traces back to a fact you were "
            "actually given."
        ),
        llm=get_llm(),
        verbose=True,
        allow_delegation=False,
        max_iter=3,
        memory=True
    )


def get_writer():
    """
    Receives the Analyst's fully-enriched JSON object (via Task.context) and
    renders it into the final markdown intelligence report.
    """
    return Agent(
        role="Intelligence Report Writer",
        goal=(
            "Read the JSON data provided in your task context and transform it "
            "into a clear, professional markdown intelligence report. Every "
            "section must be grounded in the JSON data you were given — do not "
            "invent figures or use outside knowledge. If a field in the JSON is "
            "missing, empty, or 'Not publicly available', write 'Data unavailable' "
            "for that section instead of guessing."
        ),
        backstory=(
            "You are a technical writer who specialises in investment memos and company "
            "briefs. You write for busy founders and investors who need facts fast, and "
            "you never pad a report with information you weren't actually given."
        ),
        llm=get_llm(),
        verbose=True,
        allow_delegation=False,
        max_iter=2,
        memory=True
    )