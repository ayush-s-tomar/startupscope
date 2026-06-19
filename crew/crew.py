from crewai import Crew, Process
from crew.agents import get_researcher, get_analyst, get_writer
from crew.tasks import get_research_task, get_analysis_task, get_writing_task
import time


def run_crew(company_name: str, max_retries: int = 2) -> tuple:
    """
    Runs the 3-agent crew for a given company.
    Automatically retries on failure (e.g. Groq tool-call formatting glitches)
    up to `max_retries` times before raising the final error.
    """
    last_error = None

    for attempt in range(1, max_retries + 2):  # +2 so max_retries=2 means 3 total attempts
        try:
            researcher = get_researcher()
            analyst = get_analyst()
            writer = get_writer()

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

            return result_str, None  # no file saved; history handled by app.py

        except Exception as e:
            last_error = e
            is_last_attempt = attempt == (max_retries + 1)

            if is_last_attempt:
                raise RuntimeError(
                    f"Failed after {attempt} attempt(s). Last error: {str(last_error)}"
                ) from last_error
            else:
                time.sleep(2)
                continue