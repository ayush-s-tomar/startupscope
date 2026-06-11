from crewai_tools import tool
import requests
import os
from dotenv import load_dotenv

load_dotenv()

@tool("Search the internet")
def get_search_tool(query: str) -> str:
    """Search the internet for information about a company or topic."""
    api_key = os.getenv("SERPER_API_KEY")
    headers = {"X-API-KEY": api_key, "Content-Type": "application/json"}
    payload = {"q": query, "num": 5}
    response = requests.post(
        "https://google.serper.dev/search",
        headers=headers,
        json=payload
    )
    results = response.json()
    output = ""
    for r in results.get("organic", []):
        output += f"Title: {r.get('title')}\nSnippet: {r.get('snippet')}\nLink: {r.get('link')}\n\n"
    return output or "No results found."