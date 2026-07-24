from crewai import Crew, Process
from crew.agents import get_researcher, get_analyst, get_writer, PRIMARY_MODEL, FALLBACK_MODEL
from crew.tasks import get_research_task, get_analysis_task, get_writing_task
import time
import json
import re
import os
from datetime import datetime


OUTPUTS_DIR = os.path.join(os.path.dirname(__file__), "..", "outputs")
os.makedirs(OUTPUTS_DIR, exist_ok=True)


def _empty_schema(company_name):
    return {
        "company": company_name,
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "overview": "",
        "quick_facts": {
            "founded": "",
            "hq": "",
            "team_size": "",
            "total_raised": "",
            "last_round": ""
        },
        "what_they_do": "",
        "business_model": "",
        "strengths": [],
        "risks": [],
        "competitors": [],
        "recent_news": [],
        "verdict": "",
        "verdict_rationale": ""
    }


def _extract_json(text):
    text = text.strip()
    fence_match = re.search(r"```(?:json)?\s*(.*?)\s*```", text, re.DOTALL)
    if fence_match:
        text = fence_match.group(1).strip()
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1 and end > start:
        text = text[start:end + 1]
    return json.loads(text)


def _schema_from_analysis_json(analysis_raw, company_name):
    schema = _empty_schema(company_name)
    try:
        data = _extract_json(analysis_raw)
    except (json.JSONDecodeError, ValueError):
        return schema

    schema["overview"] = data.get("product_summary", "")
    schema["quick_facts"] = {
        "founded": data.get("founded", ""),
        "hq": data.get("hq", ""),
        "team_size": data.get("team_size", ""),
        "total_raised": data.get("funding", {}).get("total_raised", ""),
        "last_round": data.get("funding", {}).get("last_round", ""),
    }
    schema["what_they_do"] = data.get("product_summary", "")
    schema["business_model"] = data.get("business_model", "")
    schema["strengths"] = data.get("strengths", [])
    schema["risks"] = data.get("risks", [])
    schema["competitors"] = data.get("competitors", [])
    schema["recent_news"] = data.get("recent_news", [])
    schema["verdict"] = data.get("verdict", "")
    schema["verdict_rationale"] = data.get("verdict_rationale", "")
    return schema


def _parse_markdown_to_schema(md, company_name):
    schema = _empty_schema(company_name)

    def _between(md, start_header, end_headers):
        pattern = r"##\s+" + re.escape(start_header) + r"\s*\n(.*?)(?=\n##\s+(?:" + "|".join(end_headers) + r")|$)"
        m = re.search(pattern, md, re.DOTALL | re.IGNORECASE)
        return m.group(1).strip() if m else ""

    all_sections = [
        "Overview", "Quick Facts", "What They Do", "Business Model",
        "Strengths", "Risks", "Competitive Landscape", "Recent News", "Verdict"
    ]

    schema["overview"] = _between(md, "Overview", all_sections[1:])

    qf_block = _between(md, "Quick Facts", all_sections[2:])
    for line in qf_block.splitlines():
        row = [c.strip() for c in line.split("|") if c.strip()]
        if len(row) == 2:
            key, val = row[0].lower(), row[1]
            if "founded" in key:
                schema["quick_facts"]["founded"] = val
            elif "hq" in key:
                schema["quick_facts"]["hq"] = val
            elif "team" in key:
                schema["quick_facts"]["team_size"] = val
            elif "raised" in key:
                schema["quick_facts"]["total_raised"] = val
            elif "round" in key:
                schema["quick_facts"]["last_round"] = val

    schema["what_they_do"] = _between(md, "What They Do", all_sections[4:])
    schema["business_model"] = _between(md, "Business Model", all_sections[5:])

    s_block = _between(md, "Strengths", all_sections[6:])
    schema["strengths"] = [
        line.lstrip("-*").strip()
        for line in s_block.splitlines()
        if line.strip().startswith(("-", "*"))
    ]

    r_block = _between(md, "Risks", all_sections[7:])
    schema["risks"] = [
        line.lstrip("-*").strip()
        for line in r_block.splitlines()
        if line.strip().startswith(("-", "*"))
    ]

    v_block = _between(md, "Verdict", [])
    for word in ["Promising", "Neutral", "Risky"]:
        if word.lower() in v_block.lower():
            schema["verdict"] = word
            break
    rationale = re.sub(r"\*\*(Promising|Neutral|Risky)\*\*", "", v_block).strip()
    schema["verdict_rationale"] = rationale

    return schema


def _timestamp():
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def _safe_name(company_name):
    return re.sub(r"[^\w]", "_", company_name.lower())


def _save_outputs(company_name, md_report, schema):
    ts = _timestamp()
    base = _safe_name(company_name) + "_" + ts

    md_path = os.path.join(OUTPUTS_DIR, base + ".md")
    json_path = os.path.join(OUTPUTS_DIR, base + ".json")

    with open(md_path, "w", encoding="utf-8") as f:
        f.write(md_report)

    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(schema, f, indent=2, ensure_ascii=False)

    return {"md": md_path, "json": json_path}


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
_QUOTA_EXHAUSTED_ERRORS = (
    "tokens per day",
    "requests per day",
    "tpd)",
    "rpd)",
)
_BASE_BACKOFF = 2
_MAX_BACKOFF = 65


def _classify_error(error_msg):
    msg = error_msg.lower()
    if any(e in msg for e in _TOOL_CALL_ERRORS):
        return "tool_call"
    if any(e in msg for e in _QUOTA_EXHAUSTED_ERRORS):
        return "quota_exhausted"
    if any(e in msg for e in _RATE_LIMIT_ERRORS):
        return "rate_limit"
    return "unknown"


def _suggested_wait(error_msg):
    ms_match = re.search(r"try again in\s+([\d.]+)ms", error_msg, re.IGNORECASE)
    if ms_match:
        seconds = float(ms_match.group(1)) / 1000.0
        return max(seconds + 5.0, 10.0)

    s_match = re.search(r"try again in\s+([\d.]+)s", error_msg, re.IGNORECASE)
    if s_match:
        return float(s_match.group(1)) + 3.0

    return 0.0


def _backoff(attempt, error_type, error_msg=""):
    if error_type == "rate_limit":
        suggested = _suggested_wait(error_msg)
        if suggested:
            return suggested
        return min(15 * (2 ** (attempt - 1)), _MAX_BACKOFF)
    return min(_BASE_BACKOFF * (2 ** (attempt - 1)), _MAX_BACKOFF)


def _run_stage(agents, tasks, current_model, stage_name):
    stage_crew = Crew(
        agents=agents,
        tasks=tasks,
        process=Process.sequential,
        verbose=True
    )
    print("[crew] Running stage: " + stage_name + " on " + current_model)
    return stage_crew.kickoff()


def run_crew(company_name, max_retries=4):
    total_attempts = max_retries + 1
    last_error = None
    current_model = PRIMARY_MODEL

    for attempt in range(1, total_attempts + 1):
        try:
            researcher = get_researcher(model=current_model)
            analyst = get_analyst(model=current_model)
            writer = get_writer(model=current_model)

            research_task = get_research_task(researcher, company_name)
            analysis_task = get_analysis_task(analyst, company_name)
            writing_task = get_writing_task(writer, company_name)

            analysis_task.context = [research_task]
            writing_task.context = [research_task, analysis_task]

            _run_stage([researcher], [research_task], current_model, "research")

            # Both PRIMARY_MODEL and FALLBACK_MODEL share the same 8000 TPM
            # cap on Groq's free tier, so both need the full cooldown to let
            # the 60s TPM window actually clear before the next call.
            cooldown_1 = 35
            time.sleep(cooldown_1)

            _run_stage([analyst], [analysis_task], current_model, "analysis")

            cooldown_2 = 30
            time.sleep(cooldown_2)

            result = _run_stage([writer], [writing_task], current_model, "writing")
            md_report = str(result)

            analysis_raw = getattr(analysis_task.output, "raw", "") or ""
            schema = _schema_from_analysis_json(analysis_raw, company_name)
            if not any([schema["strengths"], schema["risks"], schema["verdict"]]):
                schema = _parse_markdown_to_schema(md_report, company_name)

            saved_paths = _save_outputs(company_name, md_report, schema)

            print("[crew] Saved: " + saved_paths["md"])
            print("[crew] Saved: " + saved_paths["json"])

            return md_report, saved_paths

        except Exception as e:
            last_error = e
            error_msg = str(e)
            error_type = _classify_error(error_msg)

            should_switch = (
                current_model != FALLBACK_MODEL and (
                    error_type == "quota_exhausted"
                    or (error_type == "rate_limit" and attempt >= 2)
                )
            )

            if should_switch:
                reason = "Daily quota exhausted" if error_type == "quota_exhausted" else "Repeated TPM rate limits"
                print("[Attempt " + str(attempt) + "/" + str(total_attempts) + "] " + reason + " on " + current_model + " -- switching to " + FALLBACK_MODEL)
                current_model = FALLBACK_MODEL
                wait = 2.0
            else:
                wait = _backoff(attempt, error_type, error_msg)

            if attempt < total_attempts:
                print("[Attempt " + str(attempt) + "/" + str(total_attempts) + "] " + error_type + " -- retrying in " + str(round(wait)) + "s")
                time.sleep(wait)
            else:
                raise RuntimeError(
                    "Failed after " + str(attempt) + " attempt(s) for '" + company_name + "'. Last error (" + error_type + "): " + error_msg
                ) from last_error