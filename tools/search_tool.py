from crewai.tools import tool
import requests
import os
from dotenv import load_dotenv

load_dotenv()

# ── Credibility scoring ─────────────────────────────────────────────────────
# Domains are grouped into tiers. Any domain not listed scores 0 (neutral).
# Score is added to each result so agents see best sources first.

_DOMAIN_SCORES = {
    # Tier 1 — primary startup/finance sources (score: 3)
    "crunchbase.com": 3, "techcrunch.com": 3, "bloomberg.com": 3,
    "reuters.com": 3, "forbes.com": 3, "inc.com": 3,
    "wsj.com": 3, "ft.com": 3, "businessinsider.com": 3,

    # Tier 2 — good secondary sources (score: 2)
    "linkedin.com": 2, "tracxn.com": 2, "pitchbook.com": 2,
    "venturebeat.com": 2, "wired.com": 2, "theverge.com": 2,
    "economictimes.com": 2, "yourstory.com": 2, "entrackr.com": 2,
    "moneycontrol.com": 2, "livemint.com": 2,

    # Tier 3 — acceptable general sources (score: 1)
    "wikipedia.org": 1, "medium.com": 1, "substack.com": 1,
    "github.com": 1, "producthunt.com": 1,

    # Tier -1 — low-quality / SEO spam (deprioritise)
    "quora.com": -1, "reddit.com": -1,
}


def _score(link: str) -> int:
    """Return credibility score for a URL based on its domain."""
    if not link:
        return 0
    for domain, score in _DOMAIN_SCORES.items():
        if domain in link:
            return score
    return 0


def _format_results(results: list[dict], source_tag: str) -> str:
    """Sort by credibility score and format as readable text for agents."""
    scored = sorted(results, key=lambda r: r.get("_score", 0), reverse=True)
    lines = []
    for r in scored:
        score_label = f"[credibility: {r['_score']:+d}]" if r["_score"] != 0 else ""
        lines.append(
            f"[{source_tag}] {score_label}\n"
            f"Title:   {r.get('title', 'N/A')}\n"
            f"Snippet: {r.get('snippet', 'N/A')}\n"
            f"Link:    {r.get('link', 'N/A')}\n"
        )
    return "\n".join(lines) if lines else ""


# ── Search backends ─────────────────────────────────────────────────────────

def _search_serper(query: str) -> list[dict]:
    """Primary source — Google via Serper API."""
    api_key = os.getenv("SERPER_API_KEY")
    if not api_key:
        raise ValueError("SERPER_API_KEY not set")

    headers = {"X-API-KEY": api_key, "Content-Type": "application/json"}
    payload = {"q": query, "num": 6}

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
        results.append({
            "title":   r.get("title", ""),
            "snippet": r.get("snippet", ""),
            "link":    link,
            "_score":  _score(link)
        })
    return results


def _search_duckduckgo(query: str) -> list[dict]:
    """
    Fallback source — DuckDuckGo Instant Answer API.
    Free, no key needed, but returns fewer results than Serper.
    """
    response = requests.get(
        "https://api.duckduckgo.com/",
        params={"q": query, "format": "json", "no_redirect": 1, "no_html": 1},
        timeout=10,
        headers={"User-Agent": "StartupScope/1.0"}
    )
    response.raise_for_status()
    data = response.json()

    results = []

    # RelatedTopics is DDG's main result list
    for item in data.get("RelatedTopics", []):
        # Some items are topic groups with nested Topics
        if "Topics" in item:
            for sub in item["Topics"]:
                link = sub.get("FirstURL", "")
                text = sub.get("Text", "")
                if text:
                    results.append({
                        "title":   text[:80],
                        "snippet": text,
                        "link":    link,
                        "_score":  _score(link)
                    })
        else:
            link = item.get("FirstURL", "")
            text = item.get("Text", "")
            if text:
                results.append({
                    "title":   text[:80],
                    "snippet": text,
                    "link":    link,
                    "_score":  _score(link)
                })

    # Also grab the abstract if available (Wikipedia-style summary)
    abstract = data.get("AbstractText", "")
    abstract_url = data.get("AbstractURL", "")
    if abstract:
        results.append({
            "title":   data.get("Heading", query),
            "snippet": abstract,
            "link":    abstract_url,
            "_score":  _score(abstract_url)
        })

    return results[:6]  # cap to match Serper result count


# ── Public tool ─────────────────────────────────────────────────────────────

@tool("search_the_internet")
def search_the_internet(query: str) -> str:
    """
    Search the internet for information about a company or topic.
    Uses Serper (Google) as primary source with automatic DuckDuckGo fallback.
    Results are ranked by source credibility before being returned to the agent.
    """
    # ── Step 1: Try Serper ──────────────────────────────────────────────────
    serper_results = []
    serper_error   = None

    try:
        serper_results = _search_serper(query)
    except Exception as e:
        serper_error = str(e)

    if serper_results:
        output = _format_results(serper_results, source_tag="Serper/Google")
        return output or "No results found via Serper."

    # ── Step 2: Serper failed — fall back to DuckDuckGo ────────────────────
    print(f"[search_tool] Serper unavailable ({serper_error}) — switching to DuckDuckGo.")

    try:
        ddg_results = _search_duckduckgo(query)
    except Exception as e:
        return (
            f"Both search sources failed.\n"
            f"Serper error:     {serper_error}\n"
            f"DuckDuckGo error: {str(e)}"
        )

    if ddg_results:
        output = _format_results(ddg_results, source_tag="DuckDuckGo")
        return output or "No results found via DuckDuckGo."

    return "No results found from any source."