from crewai import Agent, LLM
from tools.search_tool import get_search_tool
from dotenv import load_dotenv
import os
 
load_dotenv()
 
def get_llm():
    return LLM(
        model="groq/llama-3.3-70b-versatile",
        api_key=os.getenv("GROQ_API_KEY"),
        temperature=0.3
    )
 
def get_researcher():
    return Agent(
        role="Startup Research Specialist",
        goal=(
            "Find comprehensive, up-to-date information about the given startup. "
            "Gather data on their product, funding, team, competitors, and recent news."
        ),
        backstory=(
            "You are an expert startup analyst who has spent 10 years researching "
            "tech companies for venture capital firms."
        ),
        tools=[get_search_tool],
        llm=get_llm(),
        verbose=True,
        allow_delegation=False,
        max_iter=3
    )
 
def get_analyst():
    return Agent(
        role="Business Intelligence Analyst",
        goal=(
            "Take raw research data and extract the most important business insights. "
            "Identify strengths, weaknesses, opportunities, and red flags."
        ),
        backstory=(
            "You are a senior business analyst who has evaluated hundreds of startups."
        ),
        llm=get_llm(),
        verbose=True,
        allow_delegation=False,
        max_iter=2
    )
 
def get_writer():
    return Agent(
        role="Intelligence Report Writer",
        goal=(
            "Transform structured analysis into a clear, professional intelligence "
            "report that a founder, investor, or job candidate can act on immediately."
        ),
        backstory=(
            "You are a technical writer who specialises in investment memos and company briefs."
        ),
        llm=get_llm(),
        verbose=True,
        allow_delegation=False,
        max_iter=2
    )
 