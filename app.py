import re
import threading
import time
import uuid
from datetime import datetime, timezone

from fastapi import FastAPI, HTTPException, Response
from fastapi.responses import PlainTextResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from history import add_entry, clear_history, load_history
from crew.crew import run_crew

app = FastAPI(title="StartupScope API")

# ── In-memory job store ─────────────────────────────────────────────────
# Single-process, single-dyno deployment (Render free/starter web service).
# Jobs live only as long as the process does -- fine for this use case,
# since finished reports are persisted separately via history.py / outputs/.
_JOBS: dict[str, dict] = {}
_JOBS_LOCK = threading.Lock()

_STAGE_LABELS = {
    "searching":   "🔍 Searching the web...",
    "researching": "🔍 Researcher is extracting facts...",
    "analyzing":   "📊 Analyst is extracting insights...",
    "writing":     "✍️  Writer is composing the report...",
    "finalizing":  "✅ Finalising and formatting output...",
}
_STAGE_ORDER = list(_STAGE_LABELS.keys())

MAX_RUN_SECONDS = 240


def _pdf_safe(text: str) -> str:
    replacements = {
        "\u2014": "-", "\u2013": "-",
        "\u2010": "-", "\u2011": "-",
        "\u2012": "-", "\u2015": "-",
        "\u2018": "'", "\u2019": "'",
        "\u201c": '"', "\u201d": '"',
        "\u2022": "-", "\u2026": "...",
    }
    for src, dst in replacements.items():
        text = text.replace(src, dst)
    return text.encode("latin-1", errors="replace").decode("latin-1")


def markdown_to_pdf_bytes(md_text: str, title: str = "Report") -> bytes | None:
    try:
        from fpdf import FPDF
    except ImportError:
        return None

    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()

    pdf.set_font("Helvetica", "B", 16)
    pdf.set_x(pdf.l_margin)
    pdf.multi_cell(0, 10, _pdf_safe(title))
    pdf.ln(2)

    for raw_line in md_text.splitlines():
        line = raw_line.strip()
        if not line:
            pdf.ln(3)
            continue
        pdf.set_x(pdf.l_margin)
        if line.startswith("# "):
            pdf.set_font("Helvetica", "B", 15)
            pdf.multi_cell(0, 9, _pdf_safe(line.lstrip("# ").strip()))
        elif line.startswith("## "):
            pdf.set_font("Helvetica", "B", 12)
            pdf.ln(2)
            pdf.set_x(pdf.l_margin)
            pdf.multi_cell(0, 8, _pdf_safe(line.lstrip("# ").strip()))
        elif line.startswith(("- ", "* ")):
            pdf.set_font("Helvetica", "", 10)
            clean = re.sub(r"\*\*(.*?)\*\*", r"\1", line[2:].strip())
            pdf.multi_cell(0, 6, _pdf_safe(f"  -  {clean}"))
        elif line in ("---",):
            pdf.ln(2)
        else:
            pdf.set_font("Helvetica", "", 10)
            clean = re.sub(r"\*\*(.*?)\*\*", r"\1", line)
            clean = re.sub(r"\|", "  ", clean)
            pdf.multi_cell(0, 6, _pdf_safe(clean))

    return bytes(pdf.output())


# ── Background job runner ───────────────────────────────────────────────

def _set_job(job_id, **kwargs):
    with _JOBS_LOCK:
        _JOBS[job_id].update(kwargs)


def _run_job(job_id: str, company_name: str):
    start = time.time()

    def _on_stage(stage: str):
        _set_job(
            job_id,
            stage=stage,
            stage_label=_STAGE_LABELS.get(stage, stage),
            elapsed=round(time.time() - start),
        )

    try:
        result, _paths = run_crew(company_name, progress_cb=_on_stage)
        add_entry(company_name, result, mode="single")
        _set_job(job_id, status="done", result=result, elapsed=round(time.time() - start))
    except Exception as e:  # noqa: BLE001 -- background thread boundary
        _set_job(job_id, status="error", error=str(e), elapsed=round(time.time() - start))


class RunRequest(BaseModel):
    company: str


class CompareRequest(BaseModel):
    company_a: str
    company_b: str


@app.post("/api/run")
def start_run(req: RunRequest):
    company_name = req.company.strip()
    if not company_name:
        raise HTTPException(400, "Company name is required")

    job_id = uuid.uuid4().hex
    with _JOBS_LOCK:
        _JOBS[job_id] = {
            "status": "running",
            "company": company_name,
            "stage": "searching",
            "stage_label": _STAGE_LABELS["searching"],
            "elapsed": 0,
            "result": None,
            "error": None,
            "started_at": datetime.now(timezone.utc).isoformat(),
        }

    thread = threading.Thread(target=_run_job, args=(job_id, company_name), daemon=True)
    thread.start()
    return {"job_id": job_id}


@app.get("/api/status/{job_id}")
def get_status(job_id: str):
    with _JOBS_LOCK:
        job = _JOBS.get(job_id)
    if not job:
        raise HTTPException(404, "Job not found")

    elapsed = job.get("elapsed", 0)
    progress_pct = min(elapsed / MAX_RUN_SECONDS, 0.99) if job["status"] == "running" else (1.0 if job["status"] == "done" else 0.0)

    if elapsed >= MAX_RUN_SECONDS and job["status"] == "running":
        _set_job(job_id, status="error", error=(
            f"Report generation timed out after {MAX_RUN_SECONDS}s. This usually "
            "means a network stall talking to Groq or the search provider. "
            "Please try again."
        ))
        with _JOBS_LOCK:
            job = _JOBS.get(job_id)

    return {
        "status": job["status"],
        "stage": job.get("stage"),
        "stage_label": job.get("stage_label"),
        "elapsed": elapsed,
        "progress": progress_pct,
        "result": job.get("result"),
        "error": job.get("error"),
        "company": job.get("company"),
    }


@app.get("/api/history")
def get_history():
    return load_history()


@app.get("/api/history/{entry_id}")
def get_history_entry(entry_id: str):
    for entry in load_history():
        if entry["id"] == entry_id:
            return entry
    raise HTTPException(404, "Report not found")


@app.delete("/api/history")
def delete_history():
    clear_history()
    return {"ok": True}


@app.get("/api/download/{job_id}.md")
def download_md(job_id: str):
    with _JOBS_LOCK:
        job = _JOBS.get(job_id)
    if not job or job.get("status") != "done":
        raise HTTPException(404, "Report not ready")
    filename = job["company"].lower().replace(" ", "_") + "_report.md"
    return PlainTextResponse(
        job["result"],
        media_type="text/markdown",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@app.get("/api/download/{job_id}.pdf")
def download_pdf(job_id: str):
    with _JOBS_LOCK:
        job = _JOBS.get(job_id)
    if not job or job.get("status") != "done":
        raise HTTPException(404, "Report not ready")

    pdf_bytes = markdown_to_pdf_bytes(job["result"], title=f"{job['company']} — Intelligence Report")
    if not pdf_bytes:
        raise HTTPException(500, "PDF generation unavailable (fpdf2 not installed)")

    filename = job["company"].lower().replace(" ", "_") + "_report.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


# ── Static frontend (plain HTML/CSS/JS, no Streamlit) ──────────────────
app.mount("/", StaticFiles(directory="static", html=True), name="static")