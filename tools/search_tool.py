from crewai_tools import SerperDevTool
import os
from dotenv import load_dotenv

load_dotenv()

def get_search_tool():
    return SerperDevTool(
        n_results=5,
        country="in",
        locale="en"
    )
