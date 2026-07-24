from crewai import Crew, Process
from crew.agents import get_researcher, get_analyst, get_writer
from crew.tasks import get_research_task, get_analysis_task, get_writing_task
import time
import json
import re
import os
from datetime import datetime


# ── Output directory ────────────────────────────────────────────────────────
OUTPUTS_DIR = os.path.join(os.path.dirname(__file__), "..", "outputs")
os.makedirs(OUTPUTS_DIR, exist_ok=True)


# ── Structured schema ───────────────────────────────────────────────────────

def _empty_schema(company_name: str) -> dict:
    """Returns a blank typed report schema."""
    return {
        "company":              company_name,
        "generated_at":         datetime.utcnow().isoformat() + "Z",
        "overview":             "",
        "quick_facts": {
            "founded":          "",
            "hq":               "",
            "team_size":        "",
            "total_raised":     "",
            "last_round":       ""
        },
        "what_they_do":         "",
        "business_model":       "",
        "strengths":            [],   # list of strings
        "risks":                [],   # list of strings
        "competitors": [],            # list of {"name": str, "model": str, "funding": str}
        "recent_news": [],            # list of {"headline": str, "date": str, "source": str}
        "verdict":              "",   # "Promising" | "Neutral" | "Risky"
        "verdict_rationale":    ""
    }


def _parse_markdown_to_schema(md: str, company_name: str) -> dict:
    """
    Best-effort extraction of structured data from the writer's markdown report.
    Fills the typed schema so downstream code (JSON export, future API) can
    consume individual fields without re-parsing the full markdown.
    """
    schema = _empty_schema(company_name)

    def _between(md: str, start_header: str, end_headers: list) -> str:
        """Extract text between two ## headings."""
        pattern = rf"##\s+{re.escape(start_header)}\s*\n(.*?)(?=\n##\s+(?:{'|'.join(end_headers)})|$)"
        m = re.search(pattern, md, re.DOTALL | re.IGNORECASE)
        return m.group(1).strip() if m else ""

    all_sections = [
        "Overview", "Quick Facts", "What They Do", "Business Model",
        "Strengths", "Risks", "Competitive Landscape", "Recent News", "Verdict"
    ]

    # ── Overview ──────────────────────────────────────────────────────────────
    schema["overview"] = _between(md, "Overview", all_sections[1:])

    # ── Quick Facts table ──────────────────────────────────────────────────────
    qf_block = _between(md, "Quick Facts", all_sections[2:])
    for line in qf_block.splitlines():
        row = [c.strip() for c in line.split("|") if c.strip()]
        if len(row) == 2:
            key, val = row[0].lower(), row[1]
            if "founded"  in key: schema["quick_facts"]["founded"]      = val
            elif "hq"     in key: schema["quick_facts"]["hq"]            = val
            elif "team"   in key: schema["quick_facts"]["team_size"]     = val
            elif "raised" in key: schema["quick_facts"]["total_raised"]  = val
            elif "round"  in key: schema["quick_facts"]["last_round"]    = val

    # ── What They Do ────────────────────────────────────────────────────────────
    schema["what_they_do"] = _between(md, "What They Do", all_sections[4:])

    # ── Business Model ───────────────────────────────────────────────────────────
    schema["business_model"] = _between(md, "Business Model", all_sections[5:])

    # ── Strengths (bullet list → list of strings) ──────────────────────────────
    s_block = _between(md, "Strengths", all_sections[6:])
    schema["strengths"] = [
        line.lstrip("-•* ").strip()
        for line in s_block.splitlines()
        if line.strip().startswith(("-", "•", "*"))
    ]

    # ── Risks (bullet list → list of strings) ─────────────────────────────────
    r_block = _between(md, "Risks", all_sections[7:])
    schema["risks"] = [
        line.lstrip("-•* ").strip()
        for line in r_block.splitlines()
        if line.strip().startswith(("-", "•", "*"))
    ]

    # ── Verdict ────────────────────────────────────────────────────────────────
    v_block = _between(md, "Verdict", [])
    for word in ["Promising", "Neutral", "Risky"]:
        if word.lower() in v_block.lower():
            schema["verdict"] = word
            break
    rationale = re.sub(r"\*\*(Promising|Neutral|Risky)\*\*", "", v_block).strip()
    schema["verdict_rationale"] = rationale

    return schema


# ── File export helpers ──────────────────────────────────────────────────────

def _timestamp() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def _safe_name(company_name: str) -> str:
    return re.sub(r"[^\w]", "_", company_name.lower())


def _save_outputs(company_name: str, md_report: str, schema: dict) -> dict:
    """
    Saves two files to outputs/:
      - <company>_<ts>.md    — raw markdown report
      - <company>_<ts>.json  — typed schema
    Returns a dict of saved paths.
    """
    ts   = _timestamp()
    base = f"{_safe_name(company_name)}_{ts}"

    md_path   = os.path.join(OUTPUTS_DIR, f"{base}.md")
    json_path = os.path.join(OUTPUTS_DIR, f"{base}.json")

    with open(md_path, "w", encoding="utf-8") as f:
        f.write(md_report)

    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(schema, f, indent=2, ensure_ascii=False)

    return {
        "md":   md_path,
        "json": json_path,
    }


# ── Retry config ─────────────────────────────────────────────────────────────

_TOOL_CALL_ERRORS = (
    "tool call validation failed",
    "tool_use_failed",
    "invalid_request_error",
)
_RATE_LIMIT_ERRORS = (
    "rate_limit_exceeded",
    "429",
    "too many requests",
)
_BASE_BACKOFF = 2
_MAX_BACKOFF  = 30


def _classify_error(error_msg: str) -> str:
    msg = error_msg.lower()
    if any(e in msg for e in _TOOL_CALL_ERRORS):
        return "tool_call"
    if any(e in msg for e in _RATE_LIMIT_ERRORS):
        return "rate_limit"
    return "unknown"


def _backoff(attempt: int, error_type: str) -> float:
    base = 5 if error_type == "rate_limit" else _BASE_BACKOFF
    return min(base * (2 ** (attempt - 1)), _MAX_BACKOFF)


# ── Main entry point ──────────────────────────────────────────────────────────

def run_crew(company_name: str, max_retries: int = 2) -> tuple:
    """
    Runs the 3-agent crew for a given company.

    Returns:
        (markdown_report: str, saved_paths: dict)
        saved_paths has keys: "md", "json"

    Raises:
        RuntimeError after all attempts exhausted.
    """
    total_attempts = max_retries + 1
    last_error     = None

    for attempt in range(1, total_attempts + 1):
        try:
            # ── Build agents & tasks ─────────────────────────────────────────
            researcher = get_researcher()
            analyst    = get_analyst()
            writer     = get_writer()

            research_task = get_research_task(researcher, company_name)
            analysis_task = get_analysis_task(analyst, company_name)
            writing_task  = get_writing_task(writer, company_name)

            analysis_task.context = [research_task]
            writing_task.context  = [research_task, analysis_task]

            crew = Crew(
                agents=[researcher, analyst, writer],
                tasks=[research_task, analysis_task, writing_task],
                process=Process.sequential,
                verbose=True
            )

            # ── Run crew ─────────────────────────────────────────────────────
            result    = crew.kickoff()
            md_report = str(result)

            # ── Feature G: parse markdown → typed JSON schema ─────────────────
            schema = _parse_markdown_to_schema(md_report, company_name)

            # ── Feature H: save .md + .json to outputs/ ───────────────────────
            saved_paths = _save_outputs(company_name, md_report, schema)

            print(f"[crew] Saved: {saved_paths['md']}")
            print(f"[crew] Saved: {saved_paths['json']}")

            return md_report, saved_paths

        except Exception as e:
            last_error = e
            error_msg  = str(e)
            error_type = _classify_error(error_msg)
            wait       = _backoff(attempt, error_type)

            if attempt < total_attempts:
                print(
                    f"[Attempt {attempt}/{total_attempts}] "
                    f"{error_type.replace('_', ' ').title()} — retrying in {wait:.0f}s..."
                )
                time.sleep(wait)
            else:
                raise RuntimeError(
                    f"Failed after {attempt} attempt(s) for '{company_name}'. "
                    f"Last error ({error_type}): {error_msg}"
                ) from last_error
