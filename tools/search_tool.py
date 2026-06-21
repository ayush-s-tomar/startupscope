from crewai.tools import tool
import requests
import os
from dotenv import load_dotenv

load_dotenv()

@tool("search_the_internet")
def search_the_internet(query: str) -> str:
    """Search the internet for information about a company or topic."""
    api_key = os.getenv("SERPER_API_KEY")
    if not api_key:
        return "Error: SERPER_API_KEY not set."
    
    headers = {"X-API-KEY": api_key, "Content-Type": "application/json"}
    payload = {"q": query, "num": 5}
    
    try:
        response = requests.post(
            "https://google.serper.dev/search",
            headers=headers,
            json=payload,
            timeout=10
        )
        response.raise_for_status()
        results = response.json()
    except Exception as e:
        return f"Search failed: {str(e)}"

    output = ""
    for r in results.get("organic", []):
        output += f"Title: {r.get('title')}\nSnippet: {r.get('snippet')}\nLink: {r.get('link')}\n\n"
    
    return output or "No results found."