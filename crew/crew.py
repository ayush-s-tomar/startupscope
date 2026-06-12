from crewai import Crew, Process
from crew.agents import get_researcher, get_analyst, get_writer
from crew.tasks import get_research_task, get_analysis_task, get_writing_task
from pathlib import Path
import datetime

def run_crew(company_name: str, model: str = "llama3-70b-8192", depth: str = "Quick") -> tuple:
    max_searches = 3 if depth == "Quick" else 7

    researcher = get_researcher(model=model, max_searches=max_searches)
    analyst = get_analyst(model=model)
    writer = get_writer(model=model)

    research_task = get_research_task(researcher, company_name)
    analysis_task = get_analysis_task(analyst, company_name)
    writing_task = get_writing_task(writer, company_name)

    analysis_task.context = [research_task]
    writing_task.context = [research_task, analysis_task]

    crew = Crew(
        agents=[researcher, analyst, writer],
        tasks=[research_task, analysis_task, writing_task],
        process=Process.sequential,
        verbose=True
    )

    result = crew.kickoff()
    result_str = str(result)

    Path("outputs").mkdir(exist_ok=True)
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_name = company_name.replace(" ", "_").lower()
    filename = f"outputs/{safe_name}_{timestamp}.md"

    with open(filename, "w", encoding="utf-8") as f:
        f.write(result_str)

    return result_str, filename