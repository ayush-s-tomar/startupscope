import json
import re
import os
import time
from datetime import datetime

# Must be set before crewai (or anything importing it, like crew.agents) is
# imported: crewai's telemetry module tries to register OS signal handlers
# at import/init time, which only works in the main thread. This app calls
# run_crew() from inside a background thread (see app.py's
# run_with_progress), so those registrations were failing and logging noisy
# tracebacks on every run. Disabling telemetry up front skips that
# registration entirely.
os.environ.setdefault("CREWAI_DISABLE_TELEMETRY", "true")
os.environ.setdefault("OTEL_SDK_DISABLED", "true")

from crew.agents import call_llm_with_retry
from crew.tasks import (
    RESEARCH_SYSTEM, ANALYSIS_SYSTEM, WRITER_SYSTEM,
    build_research_prompt, build_analysis_prompt, build_writing_prompt
)

try:
    from tools.search_tool import search_the_internet
except ImportError:
    search_the_internet = None


OUTPUTS_DIR = os.path.join(os.path.dirname(__file__), "..", "outputs")
os.makedirs(OUTPUTS_DIR, exist_ok=True)


# ── Search: plain Python, no LLM involved, no tokens spent here ────────────

def _call_search_tool(query):
    """
    Tries the common CrewAI tool invocation styles in order, since the
    exact interface of tools/search_tool.py wasn't available while writing
    this. If none of these match, this is the one function to fix.
    """
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
        except Exception as e:
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


# ── JSON helpers ─────────────────────────────────────────────────────────

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
        "generated_at": datetime.utcnow().isoformat() + "Z",
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

    schema["overview"] = data.get("product_summary", "")
    schema["quick_facts"] = {
        "founded": data.get("founded", ""),
        "hq": data.get("hq", ""),
        "team_size": data.get("team_size", ""),
        "total_raised": _sanitize_money_field(data.get("funding", {}).get("total_raised", "")),
        "last_round": _sanitize_money_field(data.get("funding", {}).get("last_round", "")),
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


# ── Main pipeline: 3 flat calls, nothing else touches the LLM ─────────────

def _parse_money(text):
    """
    Extracts monetary figures from text as normalized dollar floats,
    respecting decimal points and units (B/billion, M/million) instead of
    naively concatenating digits. The previous digit-strip approach treated
    '$13.2 billion' and '$132 billion' as the same because it dropped the
    decimal point -- this is exactly the kind of false match that let a
    wrong figure through the guard undetected.

    Coerces input to str first: the model has been known to return
    funding.total_raised/last_round as a raw JSON number (e.g. 3000000000)
    instead of a string like "$3B". re.finditer requires a str/bytes-like
    object and raises "expected string or bytes-like object, got 'int'"
    on a bare int/float -- this crashed the whole report generation the
    moment that happened, so every caller is protected here in one place
    rather than needing every call site to remember to cast first.
    """
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
            continue  # bare number with no unit is too ambiguous to use
        values.append(num)
    return values


_MONEY_PATTERN = re.compile(
    r"\$?\s*\d+(?:\.\d+)?\s*(?:billion|bn|b\b|million|mn|m\b)",
    re.IGNORECASE,
)


def _sanitize_money_field(value):
    """
    total_raised / last_round are supposed to be short clean values like
    '$132B' or 'Series H - $65B'. Instead the model has been known to
    return a full sentence fragment with the number buried inside it
    (e.g. '132B and a recent Series H round'), which then bleeds straight
    into the middle of a report sentence, rendering as a raw inline code
    chip in the Strengths section. Rather than trust the model to keep
    following the "keep it short" instruction, this pulls out just the
    first dollar-amount-shaped substring (plus an optional leading round
    label like 'Series H') and throws away any surrounding prose. If
    nothing money-shaped is found at all, fall back to
    'Not publicly available' rather than passing raw prose through.
    """
    if value is None or value == "":
        return value
    if not isinstance(value, str):
        # Model returned a raw JSON number instead of a string like "$3B".
        # Convert it to a plain string so the same money-shape check below
        # can run on it -- a bare number with no unit word (e.g. "3000000000")
        # won't match _MONEY_PATTERN, so this correctly falls through to the
        # "Not publicly available" branch below rather than crashing or
        # silently leaving a raw int sitting in the schema/report.
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
    """
    Prompt instructions alone weren't reliably stopping the model from
    reporting a valuation or a single round's size as total_raised. This
    parses total_raised as an actual dollar amount (respecting decimals
    and units) and checks whether a matching amount (within 2% tolerance,
    to allow minor rounding) appears anywhere in the raw search text. If
    not, it's overwritten instead of silently repeating an unsupported
    figure. It also sanitizes total_raised/last_round to short clean
    values, since the model has separately been known to bury the money
    value inside a full sentence fragment rather than returning it alone.
    """
    try:
        data = _extract_json(research_raw)
    except (json.JSONDecodeError, ValueError):
        return research_raw

    funding = data.get("funding", {})
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
    """
    Scans result_text sentence by sentence rather than treating the whole
    blob as one pool of numbers. A search for '<competitor> total funding
    raised' pulls in a lot of unrelated financial figures (parent company
    market cap, revenue, unrelated deals) -- taking the single largest
    number anywhere in that blob picked up exactly this kind of noise
    (e.g. Google's overall scale showing up as "Google DeepMind funding").

    A sentence only counts as evidence if it contains BOTH the company
    name and a funding-related keyword ('raised', 'funding', 'invested',
    etc.) -- so a stray large number elsewhere in the results, with no
    connection to the company or to funding, is ignored. Values above
    _PLAUSIBLE_FUNDING_CAP are also rejected outright as more likely to be
    a misattributed market cap/revenue number than an actual funding
    total.
    """
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
    """
    Competitor funding was always coming back 'Not publicly available' --
    not because the model was refusing to guess, but because the search
    stage (_run_searches) only ever queries for the TARGET company's
    funding. There was never any competitor funding data anywhere in the
    pipeline for the model to draw from, so 'Not publicly available' was
    the only honest answer it could give.

    This patches that gap directly: once the analysis stage has identified
    who the competitors are, run one small targeted search per competitor
    and mechanically extract a funding figure from the results using
    _extract_competitor_funding, which requires the number to appear in a
    sentence that actually mentions both the company and funding -- not
    just anywhere in the results. This does not touch the model at all --
    it's a second, narrow, plain-Python search-and-patch step.
    """
    try:
        data = _extract_json(analysis_raw)
    except (json.JSONDecodeError, ValueError):
        return analysis_raw

    competitors = data.get("competitors", [])
    if not competitors:
        return analysis_raw

    changed = False
    for comp in competitors[:max_competitors]:
        name = comp.get("name", "").strip()
        if not name:
            continue
        existing = comp.get("funding", "")
        if existing and existing != "Not publicly available":
            continue  # model already had something -- don't overwrite

        query = name + " total funding raised"
        result_text = _call_search_tool(query)
        time.sleep(1)

        best = _extract_competitor_funding(result_text, name)
        if best is not None and best >= 1_000_000:  # sanity floor
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


def _format_num(n):
    """Formats a float as a clean string, dropping a trailing '.0'."""
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
    r"\$?\d+(?:\.\d+)?\s*(?:B|billion|M|million)\s+(?:total\s+funding|funding|raised)?\s*and\s+a\s+recent[^.,;]*",
    re.IGNORECASE,
)


def _scrub_money_bleed(md_report):
    """
    The prose-bleed bug (a garbled money fragment like '132B and a recent
    Series H round' getting glued mid-sentence) was originally only fixed
    for the two structured fields (total_raised/last_round) via
    _sanitize_money_field. But the same tendency shows up anywhere the
    model writes free-text prose that mentions funding -- e.g. inside a
    strengths[] bullet -- which that field-level fix never touches. This
    is a last-resort mechanical scrub over the FINAL rendered report text,
    catching the same 'money fragment + and a recent...' shape wherever it
    appears and collapsing it down to just the clean money value.
    """
    def _clean_match(m):
        money = re.search(r"\$?\d+(?:\.\d+)?\s*(?:B|billion|M|million)", m.group(0), re.IGNORECASE)
        if not money:
            return ""
        val = money.group(0)
        if not val.startswith("$"):
            val = "$" + val
        print("[crew] scrubbed money-bleed from report: '" + m.group(0) + "' -> '" + val + "'")
        return val

    return _MONEY_BLEED_PATTERN.sub(_clean_match, md_report)


def _scrub_unsupported_infra_claims(md_report, search_text):
    """
    Prompt-level instructions failed to stop 'multi-cloud infrastructure'
    from appearing TWICE across different runs, in different stages. This
    is a mechanical last line of defense: any banned infra phrase that
    doesn't literally appear in the raw search text gets stripped from the
    final report text directly, regardless of what the model decided to
    write.
    """
    search_lower = search_text.lower()
    cleaned = md_report
    for phrase in _BANNED_INFRA_PHRASES:
        if phrase in search_lower:
            continue  # actually supported by a source, leave it
        pattern = re.compile(re.escape(phrase), re.IGNORECASE)
        if pattern.search(cleaned):
            print("[crew] stripping unsupported infra claim from report: '" + phrase + "'")
            cleaned = pattern.sub("", cleaned)
    cleaned = re.sub(r"\*\*\s*\*\*", "", cleaned)
    cleaned = re.sub(r"[ \t]{2,}", " ", cleaned)
    cleaned = re.sub(r",\s*,", ",", cleaned)
    return cleaned


_SEARCH_FAILURE_MARKERS = (
    "search tool unavailable",
    "search failed for query",
    "no results found from any source",
    "both search sources failed",
)


def _check_search_health(search_text, queries_run):
    """
    Counts how many of the individual search queries actually failed
    (matched one of the known failure-marker strings that _call_search_tool
    / search_the_internet emit on error) versus how many returned real
    content. Returns the failure reason string if ALL queries failed,
    otherwise returns None. This is checked right after search, before any
    LLM calls are made, so a total search failure is caught immediately
    instead of silently cascading into a fully empty report several stages
    later with no visible explanation of why.
    """
    blocks = search_text.split("\n\nQuery: ")
    failed = []
    for block in blocks:
        lower = block.lower()
        if any(marker in lower for marker in _SEARCH_FAILURE_MARKERS):
            failed.append(block.strip().split("\n")[-1][:200])

    if len(failed) >= queries_run and queries_run > 0:
        return failed[0] if failed else "unknown -- all queries returned empty"
    return None


def _build_search_failure_report(company_name, reason):
    """
    Instead of letting a total search failure silently cascade into a
    report where every field says 'Data unavailable' with zero
    explanation, this builds a small report that states the real reason
    directly, so it's visible on-screen without needing Cloud logs.
    """
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
    """
    True if the schema has essentially no real content -- every scalar
    field is blank/a known placeholder AND every list field is empty.
    Used to catch the case where the pipeline runs start-to-finish without
    raising any exception, but produced nothing usable (e.g. search
    returned no real content, so every downstream field is honestly
    "Not publicly available" -- correct behavior per-field, but the
    aggregate result is a useless report that gives no visibility into why).
    """
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
    """
    Counts how many of the individual 'Query: ...' blocks in search_text
    contain what looks like real content, vs. an error/empty marker. Used
    only for the diagnostics report -- a quick eyeball of search health
    without needing Cloud logs.
    """
    blocks = search_text.split("\n\nQuery: ")
    total = len(blocks)
    failed = 0
    for block in blocks:
        lower = block.lower()
        if any(marker in lower for marker in _SEARCH_FAILURE_MARKERS) or "no results found" in lower:
            failed += 1
    return total - failed, total


def _build_diagnostics_report(company_name, search_text, research_raw, analysis_raw, md_report):
    """
    Builds a version of the report with a Diagnostics section prepended,
    showing raw pipeline output at each stage. Only triggered when the
    final schema came back effectively empty. This is meant to be pasted
    directly from the app UI -- no need to dig through Cloud logs.
    """
    good_hits, total_queries = _count_search_hits(search_text)

    diag = (
        "# ⚠️ Diagnostics — " + company_name + "\n\n"
        "The report below came back with almost no real data. Here is the "
        "raw pipeline output at each stage so the cause is visible without "
        "checking Cloud logs.\n\n"
        "**Search:** " + str(good_hits) + " / " + str(total_queries) + " queries "
        "returned usable content.\n\n"
        "**First 100 chars of search text:**\n```\n" + search_text[:100].replace("`", "'") + "\n```\n\n"
        "**Research stage raw output (first 400 chars):**\n```\n" + (research_raw or "")[:400].replace("`", "'") + "\n```\n\n"
        "**Analysis stage raw output (first 400 chars):**\n```\n" + (analysis_raw or "")[:400].replace("`", "'") + "\n```\n\n"
        "---\n\n"
    )
    return diag + md_report


def run_crew(company_name, max_retries=4):
    print("[crew] Searching (plain Python, no tokens spent here)...")
    search_text = _run_searches(company_name)

    failure_reason = _check_search_health(search_text, queries_run=5)
    if failure_reason:
        print("[crew] ABORTING before LLM calls -- all searches failed: " + failure_reason)
        md_report, schema = _build_search_failure_report(company_name, failure_reason)
        saved_paths = _save_outputs(company_name, md_report, schema)
        return md_report, saved_paths

    print("[crew] Stage 1/3: research (1 flat LLM call)...")
    research_prompt = build_research_prompt(company_name, search_text)
    # gpt-oss-120b/20b are reasoning models -- part of max_tokens goes to an
    # internal reasoning trace before the actual JSON answer gets written.
    # 1500 was tight enough that the model could burn the whole budget
    # reasoning and return empty content (see agents.py's empty-completion
    # check). 2600 gives real headroom for both.
    research_raw = call_llm_with_retry(research_prompt, system=RESEARCH_SYSTEM, max_retries=max_retries, max_tokens=2600)
    research_raw = _strip_unsupported_total_raised(research_raw, search_text)

    time.sleep(15)

    print("[crew] Stage 2/3: analysis (1 flat LLM call)...")
    analysis_prompt = build_analysis_prompt(company_name, research_raw)
    analysis_raw = call_llm_with_retry(analysis_prompt, system=ANALYSIS_SYSTEM, max_retries=max_retries, max_tokens=2600)

    print("[crew] Enriching competitor funding (plain Python, targeted searches)...")
    analysis_raw = _enrich_competitor_funding(analysis_raw)

    time.sleep(15)

    print("[crew] Stage 3/3: writing (1 flat LLM call)...")
    writing_prompt = build_writing_prompt(company_name, analysis_raw)
    md_report = call_llm_with_retry(writing_prompt, system=WRITER_SYSTEM, max_retries=max_retries, max_tokens=2000)
    md_report = _scrub_money_bleed(md_report)
    md_report = _scrub_unsupported_infra_claims(md_report, search_text)
    md_report = md_report.replace("`", "")

    schema = _schema_from_analysis_json(analysis_raw, company_name)

    if _is_effectively_empty(schema):
        print("[crew] WARNING: final schema is effectively empty -- attaching diagnostics to report")
        md_report = _build_diagnostics_report(company_name, search_text, research_raw, analysis_raw, md_report)

    saved_paths = _save_outputs(company_name, md_report, schema)

    print("[crew] Saved: " + saved_paths["md"])
    print("[crew] Saved: " + saved_paths["json"])

    return md_report, saved_paths