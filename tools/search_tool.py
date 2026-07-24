from crewai.tools import tool
import requests
import os
from dotenv import load_dotenv

load_dotenv()


def get_secret(key):
    try:
        import streamlit as st
        if key in st.secrets:
            return st.secrets[key]
    except Exception:
        pass
    return os.getenv(key, "")


_DOMAIN_SCORES = {
    "crunchbase.com": 3, "techcrunch.com": 3, "bloomberg.com": 3,
    "reuters.com": 3, "forbes.com": 3, "inc.com": 3,
    "wsj.com": 3, "ft.com": 3, "businessinsider.com": 3,

    "linkedin.com": 2, "tracxn.com": 2, "pitchbook.com": 2,
    "venturebeat.com": 2, "wired.com": 2, "theverge.com": 2,
    "economictimes.com": 2, "yourstory.com": 2, "entrackr.com": 2,
    "moneycontrol.com": 2, "livemint.com": 2,

    "wikipedia.org": 1, "medium.com": 1, "substack.com": 1,
    "github.com": 1, "producthunt.com": 1,

    "quora.com": -1, "reddit.com": -1,
}


def _score(link):
    if not link:
        return 0
    for domain, score in _DOMAIN_SCORES.items():
        if domain in link:
            return score
    return 0


def _format_results(results, source_tag):
    scored = sorted(results, key=lambda r: r.get("_score", 0), reverse=True)
    lines = []
    for r in scored:
        score_label = ""
        if r["_score"] != 0:
            score_label = "[credibility: " + ("+" if r["_score"] > 0 else "") + str(r["_score"]) + "]"
        snippet = (r.get("snippet") or "N/A")[:100]
        line = (
            "[" + source_tag + "] " + score_label + "\n"
            "Title:   " + r.get("title", "N/A") + "\n"
            "Snippet: " + snippet + "\n"
            "Link:    " + r.get("link", "N/A") + "\n"
        )
        lines.append(line)
    return "\n".join(lines) if lines else ""


def _search_serper(query):
    api_key = get_secret("SERPER_API_KEY")
    if not api_key:
        raise ValueError("SERPER_API_KEY not set")

    headers = {"X-API-KEY": api_key, "Content-Type": "application/json"}
    payload = {"q": query, "num": 2}

    response = requests.post(
        "https://google.serper.dev/search",
        headers=headers,
        json=payload,
        timeout=10
    )
    response.raise_for_status()
    raw = response.json().get("organic", [])

    results = []
    for r in raw:
        link = r.get("link", "")
        entry = {
            "title": r.get("title", ""),
            "snippet": r.get("snippet", ""),
            "link": link,
            "_score": _score(link)
        }
        results.append(entry)
    return results


def _search_duckduckgo(query):
    response = requests.get(
        "https://api.duckduckgo.com/",
        params={"q": query, "format": "json", "no_redirect": 1, "no_html": 1},
        timeout=10,
        headers={"User-Agent": "StartupScope/1.0"}
    )
    response.raise_for_status()
    data = response.json()

    results = []

    for item in data.get("RelatedTopics", []):
        if "Topics" in item:
            for sub in item["Topics"]:
                link = sub.get("FirstURL", "")
                text = sub.get("Text", "")
                if text:
                    entry = {
                        "title": text[:80],
                        "snippet": text,
                        "link": link,
                        "_score": _score(link)
                    }
                    results.append(entry)
        else:
            link = item.get("FirstURL", "")
            text = item.get("Text", "")
            if text:
                entry = {
                    "title": text[:80],
                    "snippet": text,
                    "link": link,
                    "_score": _score(link)
                }
                results.append(entry)

    abstract = data.get("AbstractText", "")
    abstract_url = data.get("AbstractURL", "")
    if abstract:
        entry = {
            "title": data.get("Heading", query),
            "snippet": abstract,
            "link": abstract_url,
            "_score": _score(abstract_url)
        }
        results.append(entry)

    return results[:2]


@tool("search_the_internet")
def search_the_internet(query):
    """
    Search the internet for information about a company or topic.
    Uses Serper (Google) as primary source with automatic DuckDuckGo fallback.
    Results are ranked by source credibility before being returned to the agent.
    """
    serper_results = []
    serper_error = None

    try:
        serper_results = _search_serper(query)
    except Exception as e:
        serper_error = str(e)

    if serper_results:
        output = _format_results(serper_results, "Serper/Google")
        return output or "No results found via Serper."

    print("[search_tool] Serper unavailable (" + str(serper_error) + ") -- switching to DuckDuckGo.")

    try:
        ddg_results = _search_duckduckgo(query)
    except Exception as e:
        return "Both search sources failed.\nSerper error: " + str(serper_error) + "\nDuckDuckGo error: " + str(e)

    if ddg_results:
        output = _format_results(ddg_results, "DuckDuckGo")
        return output or "No results found via DuckDuckGo."

    return "No results found from any source."