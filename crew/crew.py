import json
import os
import re
import time
from datetime import datetime, timezone

os.environ.setdefault("CREWAI_DISABLE_TELEMETRY", "true")
os.environ.setdefault("OTEL_SDK_DISABLED", "true")

from crew.tasks import (
    ANALYSIS_SYSTEM,
    RESEARCH_SYSTEM,
    WRITER_SYSTEM,
    build_analysis_prompt,
    build_research_prompt,
    build_writing_prompt,
)

from crew.agents import DEFAULT_MAX_RETRIES, call_llm_with_retry

try:
    from tools.search_tool import search_the_internet
except ImportError:
    search_the_internet = None


OUTPUTS_DIR = os.path.join(os.path.dirname(__file__), "..", "outputs")
os.makedirs(OUTPUTS_DIR, exist_ok=True)


def _call_search_tool(query):
    if search_the_internet is None:
        return "(search tool unavailable: tools/search_tool.py not found)"

    attempts = [
        lambda: search_the_internet._run(query=query),
        lambda: search_the_internet._run(query),
        lambda: search_the_internet.run(query=query),
        lambda: search_the_internet.run(query),
        lambda: search_the_internet.func(query),
        lambda: search_the_internet(query),
    ]
    last_error = None
    for attempt in attempts:
        try:
            result = attempt()
            if result:
                return str(result)
        except Exception as e:  # noqa: BLE001
            last_error = e
            continue
    return "(search failed for query '" + query + "': " + str(last_error) + ")"


def _run_searches(company_name):
    queries = [
        company_name + " funding investors business model",
        company_name + " competitors news 2024 2025",
        company_name + " founded headquarters employees team size",
        company_name + " total funding raised to date valuation",
        company_name + " technology stack product features platform",
    ]
    results = []
    for q in queries:
        results.append("Query: " + q + "\n" + _call_search_tool(q))
        time.sleep(1)
    return "\n\n".join(results)


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


def _empty_schema(company_name):
    return {
        "company": company_name,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "overview": "",
        "quick_facts": {
            "founded": "", "hq": "", "team_size": "",
            "total_raised": "", "last_round": ""
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


def _schema_from_analysis_json(analysis_raw, company_name):
    schema = _empty_schema(company_name)
    try:
        data = _extract_json(analysis_raw)
    except (json.JSONDecodeError, ValueError) as e:
        print("[crew] WARNING: analysis JSON failed to parse (" + str(e) + "). Raw text was:")
        print(analysis_raw[:500])
        return schema

    funding = data.get("funding", {})
    if not isinstance(funding, dict):
        print("[crew] WARNING: 'funding' was not an object (" + type(funding).__name__ + ") in analysis stage -- coercing")
        funding = {"total_raised": str(funding) if funding else "", "last_round": "", "investors": []}

    competitors = data.get("competitors", [])
    if not isinstance(competitors, list):
        competitors = []
    fixed_competitors = []
    for comp in competitors:
        if isinstance(comp, dict):
            fixed_competitors.append(comp)
        elif isinstance(comp, str) and comp.strip():
            fixed_competitors.append({"name": comp.strip(), "model": "Not publicly available", "funding": "Not publicly available"})

    schema["overview"] = data.get("product_summary", "")
    schema["quick_facts"] = {
        "founded": data.get("founded", ""),
        "hq": data.get("hq", ""),
        "team_size": data.get("team_size", ""),
        "total_raised": _sanitize_money_field(funding.get("total_raised", "")),
        "last_round": _sanitize_money_field(funding.get("last_round", "")),
    }
    schema["what_they_do"] = data.get("product_summary", "")
    schema["business_model"] = data.get("business_model", "")
    schema["strengths"] = data.get("strengths", [])
    schema["risks"] = data.get("risks", [])
    schema["competitors"] = fixed_competitors
    schema["recent_news"] = data.get("recent_news", [])
    schema["verdict"] = data.get("verdict", "")
    schema["verdict_rationale"] = data.get("verdict_rationale", "")
    return schema


def _timestamp():
    return datetime.now().strftime("%Y%m%d_%H%M%S")  # noqa: DTZ005


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


def _parse_money(text):
    text = str(text) if text is not None else ""
    values = []
    for match in re.finditer(r"\$?\s*(\d+(?:\.\d+)?)\s*(billion|bn|b\b|million|mn|m\b)?", text, re.IGNORECASE):
        num_str, unit = match.group(1), (match.group(2) or "").lower()
        try:
            num = float(num_str)
        except ValueError:
            continue
        if unit.startswith("b"):
            num *= 1_000_000_000
        elif unit.startswith("m"):
            num *= 1_000_000
        else:
            continue
        values.append(num)
    return values


_MONEY_PATTERN = re.compile(
    r"\$?\s*\d+(?:\.\d+)?\s*(?:billion|bn|b\b|million|mn|m\b)",
    re.IGNORECASE,
)


def _sanitize_money_field(value):
    if value is None or value == "":
        return value
    if not isinstance(value, str):
        value = str(value)

    value = value.strip()

    money_match = _MONEY_PATTERN.search(value)
    if not money_match:
        print("[crew] total_raised/last_round field had no recognizable money value in: '" + value + "' -- overwriting to 'Not publicly available'")
        return "Not publicly available"

    prefix_window = value[max(0, money_match.start() - 20):money_match.start()]
    round_match = re.search(r"(Series\s+[A-Z]|Seed|Pre-Seed)\s*[-:]?\s*$", prefix_window, re.IGNORECASE)

    cleaned = money_match.group(0).strip()
    if not cleaned.startswith("$"):
        cleaned = "$" + cleaned
    if round_match:
        cleaned = round_match.group(1) + " - " + cleaned

    reconstructed = re.escape(cleaned).replace(r"\$", r"\$?")
    if re.fullmatch(reconstructed, value, re.IGNORECASE):
        return value

    print("[crew] sanitized money field: '" + value + "' -> '" + cleaned + "'")
    return cleaned


def _strip_unsupported_total_raised(research_raw, search_text):
    try:
        data = _extract_json(research_raw)
    except (json.JSONDecodeError, ValueError):
        return research_raw

    funding = data.get("funding", {})
    if not isinstance(funding, dict):
        print("[crew] WARNING: 'funding' was not an object (" + type(funding).__name__ + ") in research stage -- coercing")
        funding = {"total_raised": str(funding) if funding else "", "last_round": "", "investors": []}
        data["funding"] = funding
    changed = False

    total_raised = funding.get("total_raised", "")
    if total_raised and total_raised != "Not publicly available":
        sanitized = _sanitize_money_field(total_raised)
        if sanitized != total_raised:
            funding["total_raised"] = sanitized
            total_raised = sanitized
            changed = True

        if total_raised != "Not publicly available":
            claimed = _parse_money(total_raised)
            source_values = _parse_money(search_text)
            supported = any(
                c > 0 and any(abs(c - s) / c < 0.02 for s in source_values)
                for c in claimed
            )
            if claimed and not supported:
                print("[crew] total_raised '" + total_raised + "' has no matching figure in search text -- overwriting to 'Not publicly available'")
                funding["total_raised"] = "Not publicly available"
                changed = True

    last_round = funding.get("last_round", "")
    if last_round and last_round != "Not publicly available":
        sanitized = _sanitize_money_field(last_round)
        if sanitized != last_round:
            funding["last_round"] = sanitized
            changed = True

    if changed:
        data["funding"] = funding
        return json.dumps(data)

    return research_raw


_FUNDING_KEYWORDS = re.compile(r"\b(raised|funding|invested|investment|valuation|valued)\b", re.IGNORECASE)

_PLAUSIBLE_FUNDING_CAP = 300_000_000_000


def _extract_competitor_funding(result_text, name):
    name_lower = name.lower()
    sentences = re.split(r"(?<=[.!?])\s+", result_text)
    candidates = []
    for sentence in sentences:
        if name_lower not in sentence.lower():
            continue
        if not _FUNDING_KEYWORDS.search(sentence):
            continue
        for v in _parse_money(sentence):
            if v <= _PLAUSIBLE_FUNDING_CAP:
                candidates.append(v)

    if not candidates:
        return None
    return max(candidates)


def _enrich_competitor_funding(analysis_raw, max_competitors=3):
    try:
        data = _extract_json(analysis_raw)
    except (json.JSONDecodeError, ValueError):
        return analysis_raw

    competitors = data.get("competitors", [])
    if not competitors:
        return analysis_raw

    changed = False
    for i, comp in enumerate(competitors):
        if not isinstance(comp, dict):
            print("[crew] WARNING: competitor entry was not an object (" + type(comp).__name__ + ") -- coercing: '" + str(comp)[:60] + "'")
            comp = {"name": str(comp).strip(), "model": "Not publicly available", "funding": "Not publicly available"}
            competitors[i] = comp
            changed = True

    for comp in competitors[:max_competitors]:
        name = comp.get("name", "").strip()
        if not name:
            continue
        existing = comp.get("funding", "")
        if existing and existing != "Not publicly available":
            continue

        query = name + " total funding raised"
        result_text = _call_search_tool(query)
        time.sleep(1)

        best = _extract_competitor_funding(result_text, name)
        if best is not None and best >= 1_000_000:
            if best >= 1_000_000_000:
                display = "$" + _format_num(best / 1_000_000_000) + "B"
            else:
                display = "$" + _format_num(best / 1_000_000) + "M"
            print("[crew] enriched competitor funding: '" + name + "' -> '" + display + "'")
            comp["funding"] = display
            changed = True
        else:
            print("[crew] no reliably-attributed funding figure found for '" + name + "' -- leaving as 'Not publicly available'")

    if changed:
        data["competitors"] = competitors
        return json.dumps(data)

    return analysis_raw


_KNOWN_SECTION_HEADINGS = [
    "Overview", "Quick Facts", "What They Do", "Business Model",
    "Strengths", "Risks", "Competitive Landscape", "Recent News", "Verdict",
]

_SQUISHED_HEADING_PATTERN = re.compile(
    r"(##\s*(?:" + "|".join(re.escape(h) for h in _KNOWN_SECTION_HEADINGS) + r"))"
    r"([A-Za-z])",
)


def _fix_squished_headings(md_report):
    def _insert_break(m):
        print("[crew] fixed squished heading: '" + m.group(0)[:40] + "...'")
        return m.group(1) + "\n\n" + m.group(2)

    return _SQUISHED_HEADING_PATTERN.sub(_insert_break, md_report)


_MISSING_HEADING_MARKER_PATTERN = re.compile(
    r"([.!?])\s*(" + "|".join(re.escape(h) for h in _KNOWN_SECTION_HEADINGS) + r")\n"
)


def _fix_missing_heading_markers(md_report):
    def _insert_heading(m):
        print("[crew] restored missing heading marker: '" + m.group(2) + "'")
        return m.group(1) + "\n\n## " + m.group(2) + "\n\n"

    return _MISSING_HEADING_MARKER_PATTERN.sub(_insert_heading, md_report)


def _format_num(n):
    if n == int(n):
        return str(int(n))
    return str(round(n, 1))


_BANNED_INFRA_PHRASES = [
    "multi-cloud", "multi cloud", "built on aws", "built on azure",
    "built on gcp", "aws infrastructure", "azure infrastructure",
    "gcp infrastructure", "cloud infrastructure", "hosted on aws",
    "hosted on azure", "hosted on gcp",
]


_MONEY_BLEED_PATTERN = re.compile(
    r"\$?\d+(?:\.\d+)?\s*(?:B|billion|M|million)"
    r"(?:\s*,)?\s*"
    r"(?:[a-z]+\s+){0,3}"
    r"(?:including|and|at|with|raised in|following|via)\s+a\s*"
    r"(?:recent\s+)?[^.,;()]*",
    re.IGNORECASE,
)


def _scrub_money_bleed(md_report):
    def _clean_match(m):
        money = re.search(r"\$?\d+(?:\.\d+)?\s*(?:B|billion|M|million)", m.group(0), re.IGNORECASE)
        if not money:
            return m.group(0)
        val = money.group(0)
        if not val.startswith("$"):
            val = "$" + val
        print("[crew] scrubbed money-bleed from report: '" + m.group(0) + "' -> '" + val + "'")
        return val

    cleaned = _MONEY_BLEED_PATTERN.sub(_clean_match, md_report)
    cleaned = re.sub(r"(\$\d+(?:\.\d+)?[BM])\(", r"\1 (", cleaned)
    return cleaned


def _scrub_unsupported_infra_claims(md_report, search_text):
    search_lower = search_text.lower()
    cleaned = md_report
    for phrase in _BANNED_INFRA_PHRASES:
        if phrase in search_lower:
            continue
        pattern = re.compile(re.escape(phrase), re.IGNORECASE)
        if pattern.search(cleaned):
            print("[crew] stripping unsupported infra claim from report: '" + phrase + "'")
            cleaned = pattern.sub("", cleaned)
    cleaned = re.sub(r"\*\*\s*\*\*", "", cleaned)
    cleaned = re.sub(r"[ \t]{2,}", " ", cleaned)
    cleaned = re.sub(r",\s*,", ",", cleaned)
    return cleaned


_COMPETITOR_MODEL_UNAVAILABLE_PATTERN = re.compile(
    r",?\s*Model:\s*Data unavailable\s*,?", re.IGNORECASE
)


def _scrub_competitor_model_placeholder(md_report):
    cleaned = _COMPETITOR_MODEL_UNAVAILABLE_PATTERN.sub("", md_report)
    cleaned = re.sub(r"\s+([.,])", r"\1", cleaned)
    cleaned = re.sub(r",\s*$", "", cleaned, flags=re.MULTILINE)
    return cleaned


_SEARCH_FAILURE_MARKERS = (
    "search tool unavailable",
    "search failed for query",
    "no results found from any source",
    "both search sources failed",
)


def _check_search_health(search_text, queries_run):
    blocks = search_text.split("\n\nQuery: ")
    failed = []
    for block in blocks:
        lower = block.lower()
        if any(marker in lower for marker in _SEARCH_FAILURE_MARKERS):
            failed.append(block.strip().split("\n")[-1][:200])

    if 0 < queries_run <= len(failed):
        return failed[0] if failed else "unknown -- all queries returned empty"
    return None


def _build_search_failure_report(company_name, reason):
    md_report = (
        "# " + company_name + " — Intelligence Report\n\n"
        "## Search Failed\n"
        "This report could not be generated because every web search "
        "query failed before reaching the AI stages.\n\n"
        "**Reason reported by the search tool:**\n\n"
        "> " + reason + "\n\n"
        "Common causes: `SERPER_API_KEY` invalid or out of quota (check "
        "Serper dashboard billing/usage), or a rate limit / network block "
        "on the search provider. No LLM tokens were spent on this run.\n"
    )
    schema = _empty_schema(company_name)
    schema["overview"] = "Search failed: " + reason
    return md_report, schema


_EMPTY_MARKERS = ("", "not publicly available", "not specified", "n/a", "unknown")


def _is_effectively_empty(schema):
    scalars = [
        schema.get("overview", ""),
        schema.get("what_they_do", ""),
        schema.get("business_model", ""),
        schema.get("quick_facts", {}).get("founded", ""),
        schema.get("quick_facts", {}).get("hq", ""),
        schema.get("quick_facts", {}).get("team_size", ""),
        schema.get("quick_facts", {}).get("total_raised", ""),
    ]
    scalars_empty = all((s or "").strip().lower() in _EMPTY_MARKERS for s in scalars)

    lists_empty = all(
        len(schema.get(k, []) or []) == 0
        for k in ("strengths", "risks", "competitors", "recent_news")
    )

    return scalars_empty and lists_empty


def _count_search_hits(search_text):
    blocks = search_text.split("\n\nQuery: ")
    total = len(blocks)
    failed = 0
    for block in blocks:
        lower = block.lower()
        if any(marker in lower for marker in _SEARCH_FAILURE_MARKERS) or "no results found" in lower:
            failed += 1
    return total - failed, total


def _build_diagnostics_report(company_name, search_text, research_raw, analysis_raw, md_report):
    good_hits, total_queries = _count_search_hits(search_text)

    diag = (
        "# ⚠️ Diagnostics — " + company_name + "\n\n"
        "The report below came back with almost no real data. Here is the "
        "raw pipeline output at each stage so the cause is visible without "
        "checking logs.\n\n"
        "**Search:** " + str(good_hits) + " / " + str(total_queries) + " queries "
        "returned usable content.\n\n"
        "**First 100 chars of search text:**\n```\n" + search_text[:100].replace("`", "'") + "\n```\n\n"
        "**Research stage raw output (first 400 chars):**\n```\n" + (research_raw or "")[:400].replace("`", "'") + "\n```\n\n"
        "**Analysis stage raw output (first 400 chars):**\n```\n" + (analysis_raw or "")[:400].replace("`", "'") + "\n```\n\n"
        "---\n\n"
    )
    return diag + md_report


def run_crew(company_name, max_retries=None, progress_cb=None):
    """
    progress_cb(stage: str) is called before each stage begins, so the
    FastAPI layer can report live progress to polling clients without
    this module knowing anything about HTTP or job queues.
    """
    if max_retries is None:
        max_retries = DEFAULT_MAX_RETRIES

    def _tick(stage):
        if progress_cb:
            try:
                progress_cb(stage)
            except Exception:  # noqa: BLE001
                pass

    _tick("searching")
    print("[crew] Searching (plain Python, no tokens spent here)...")
    search_text = _run_searches(company_name)

    failure_reason = _check_search_health(search_text, queries_run=5)
    if failure_reason:
        print("[crew] ABORTING before LLM calls -- all searches failed: " + failure_reason)
        md_report, schema = _build_search_failure_report(company_name, failure_reason)
        saved_paths = _save_outputs(company_name, md_report, schema)
        return md_report, saved_paths

    _tick("researching")
    print("[crew] Stage 1/3: research (1 flat LLM call)...")
    research_prompt = build_research_prompt(company_name, search_text)
    research_raw = call_llm_with_retry(research_prompt, system=RESEARCH_SYSTEM, max_retries=max_retries, max_tokens=2600)
    research_raw = _strip_unsupported_total_raised(research_raw, search_text)

    time.sleep(15)

    _tick("analyzing")
    print("[crew] Stage 2/3: analysis (1 flat LLM call)...")
    analysis_prompt = build_analysis_prompt(company_name, research_raw)
    analysis_raw = call_llm_with_retry(analysis_prompt, system=ANALYSIS_SYSTEM, max_retries=max_retries, max_tokens=2600)

    print("[crew] Enriching competitor funding (plain Python, targeted searches)...")
    analysis_raw = _enrich_competitor_funding(analysis_raw)

    time.sleep(15)

    _tick("writing")
    print("[crew] Stage 3/3: writing (1 flat LLM call)...")
    writing_prompt = build_writing_prompt(company_name, analysis_raw)
    md_report = call_llm_with_retry(writing_prompt, system=WRITER_SYSTEM, max_retries=max_retries, max_tokens=2000)
    md_report = md_report.replace("`", "")
    md_report = _scrub_money_bleed(md_report)
    md_report = _scrub_unsupported_infra_claims(md_report, search_text)
    md_report = _scrub_competitor_model_placeholder(md_report)
    md_report = _fix_squished_headings(md_report)
    md_report = _fix_missing_heading_markers(md_report)

    schema = _schema_from_analysis_json(analysis_raw, company_name)

    if _is_effectively_empty(schema):
        print("[crew] WARNING: final schema is effectively empty -- attaching diagnostics to report")
        md_report = _build_diagnostics_report(company_name, search_text, research_raw, analysis_raw, md_report)

    _tick("finalizing")
    saved_paths = _save_outputs(company_name, md_report, schema)

    print("[crew] Saved: " + saved_paths["md"])
    print("[crew] Saved: " + saved_paths["json"])

    return md_report, saved_paths