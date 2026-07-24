from crewai import Agent, LLM
from tools.search_tool import search_the_internet
from dotenv import load_dotenv
import os

load_dotenv()


def get_secret(key):
    try:
        import streamlit as st
        if key in st.secrets:
            return st.secrets[key]
    except Exception:
        pass
    return os.getenv(key, "")


PRIMARY_MODEL = "groq/llama-3.3-70b-versatile"
FALLBACK_MODEL = "groq/llama-3.1-8b-instant"

_MAX_RPM = {
    PRIMARY_MODEL: 15,
    FALLBACK_MODEL: 6,
}


def _rpm_for(model):
    return _MAX_RPM.get(model, 8)


def get_llm(model=None):
    return LLM(
        model=model or PRIMARY_MODEL,
        api_key=get_secret("GROQ_API_KEY"),
        temperature=0.3
    )


def get_researcher(model=None):
    model = model or PRIMARY_MODEL
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
            "well-formed JSON, never prose."
        ),
        tools=[search_the_internet],
        llm=get_llm(model),
        verbose=True,
        allow_delegation=False,
        max_iter=4,
        max_rpm=_rpm_for(model),
        memory=True
    )


def get_analyst(model=None):
    model = model or PRIMARY_MODEL
    return Agent(
        role="Business Intelligence Analyst",
        goal=(
            "Read the JSON research data provided in your task context. Base every "
            "insight strictly on that data, never invent figures or fall back on "
            "general knowledge. Output ONLY a single valid JSON object: the "
            "original fields from the research data, plus your new analysis "
            "fields. No prose, no markdown, no commentary before or after the JSON."
        ),
        backstory=(
            "You are a senior business analyst who has evaluated hundreds of startups "
            "for Series A/B investment decisions. You cut through noise and surface "
            "the 2-3 things that actually determine whether a company succeeds. You "
            "never write generic filler, every claim traces back to a fact you were "
            "actually given."
        ),
        llm=get_llm(model),
        verbose=True,
        allow_delegation=False,
        max_iter=3,
        max_rpm=_rpm_for(model),
        memory=True
    )


def get_writer(model=None):
    model = model or PRIMARY_MODEL
    return Agent(
        role="Intelligence Report Writer",
        goal=(
            "Read the JSON data provided in your task context and transform it "
            "into a clear, professional markdown intelligence report. Every "
            "section must be grounded in the JSON data you were given, do not "
            "invent figures or use outside knowledge. If a field in the JSON is "
            "missing, empty, or 'Not publicly available', write 'Data unavailable' "
            "for that section instead of guessing."
        ),
        backstory=(
            "You are a technical writer who specialises in investment memos and company "
            "briefs. You write for busy founders and investors who need facts fast, and "
            "you never pad a report with information you weren't actually given."
        ),
        llm=get_llm(model),
        verbose=True,
        allow_delegation=False,
        max_iter=2,
        max_rpm=_rpm_for(model),
        memory=True
    )