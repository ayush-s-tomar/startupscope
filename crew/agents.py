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


PRIMARY_MODEL = "groq/openai/gpt-oss-120b"
FALLBACK_MODEL = "groq/openai/gpt-oss-20b"

_MAX_RPM = {
    PRIMARY_MODEL: 15,
    FALLBACK_MODEL: 8,
}

# Both models share ONE 8000 TPM pool at the org level on Groq's free tier --
# this is not per-model. Capping max_tokens on every call keeps any single
# completion from eating most of that shared budget and starving the next
# stage in the same 60s window.
_MAX_OUTPUT_TOKENS = 900


def _rpm_for(model):
    return _MAX_RPM.get(model, 8)


def get_llm(model=None):
    return LLM(
        model=model or PRIMARY_MODEL,
        api_key=get_secret("GROQ_API_KEY"),
        temperature=0.3,
        max_tokens=_MAX_OUTPUT_TOKENS
    )


def get_researcher(model=None):
    model = model or PRIMARY_MODEL
    return Agent(
        role="Startup Research Specialist",
        goal=(
            "Find comprehensive, up-to-date information about the given startup "
            "by running multiple web searches, then output ONLY a single valid "
            "JSON object containing every finding. No prose, no markdown, no "
            "commentary before or after the JSON. Only include a fact if a search "
            "result explicitly states it -- do not infer cloud infrastructure "
            "partners, technology stacks, or API compatibility from indirect "
            "context (e.g. an investor being mentioned does not mean they are "
            "also a hosting or infrastructure partner)."
        ),
        backstory=(
            "You are an expert startup analyst who has spent 10 years researching "
            "tech companies for venture capital firms. You are meticulous about "
            "separating facts from speculation, and you always return clean, "
            "well-formed JSON, never prose. You never conflate an investor "
            "relationship with an infrastructure or technology partnership -- "
            "those are different things and you always keep them distinct."
        ),
        tools=[search_the_internet],
        llm=get_llm(model),
        verbose=True,
        allow_delegation=False,
        # Must be >= (number of searches the task requests) + 1 for the
        # final JSON answer. The task asks for 4+ searches; max_iter=3 was
        # cutting the agent off mid-search, CrewAI then forced
        # tool_choice="none" to make it answer, but the model still tried
        # to call a tool -- Groq hard-rejects that combination
        # (tool_use_failed) and it's not retryable, it fails every time.
        max_iter=6,
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
            "fields. No prose, no markdown, no commentary before or after the JSON. "
            "Do not state or imply any cloud provider, infrastructure partnership, "
            "or API compatibility claim unless it appears explicitly and literally "
            "in the research data -- if it is not there, omit it rather than "
            "inferring it from adjacent facts like investor names."
        ),
        backstory=(
            "You are a senior business analyst who has evaluated hundreds of startups "
            "for Series A/B investment decisions. You cut through noise and surface "
            "the 2-3 things that actually determine whether a company succeeds. You "
            "never write generic filler, every claim traces back to a fact you were "
            "actually given. You are especially careful never to confuse an investor "
            "relationship with a technical or infrastructure partnership."
        ),
        llm=get_llm(model),
        verbose=True,
        allow_delegation=False,
        max_iter=2,
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
            "for that section instead of guessing. Never add cloud provider names, "
            "infrastructure partnerships, or API compatibility claims that are not "
            "explicitly present in the JSON, even if they seem plausible based on "
            "general knowledge of the industry."
        ),
        backstory=(
            "You are a technical writer who specialises in investment memos and company "
            "briefs. You write for busy founders and investors who need facts fast, and "
            "you never pad a report with information you weren't actually given, "
            "especially technical claims about infrastructure or API design that could "
            "be factually wrong and embarrass the reader if repeated."
        ),
        llm=get_llm(model),
        verbose=True,
        allow_delegation=False,
        max_iter=2,
        max_rpm=_rpm_for(model),
        memory=True
    )