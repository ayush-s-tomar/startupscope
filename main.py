from crew.crew import run_crew
import argparse
import csv
import os
import time
import sys

# ── Rate-limit config from env (Feature J) ──────────────────────────────────
# Set these in your .env locally (this file is CLI-only and never runs on
# Streamlit Cloud, so it keeps using plain env vars / .env — no st.secrets needed).
# MAX_RETRIES     — how many times to retry a failed company (default 2)
# BATCH_DELAY     — seconds to wait between companies in batch mode (default 15)
#                   keeps you safely under Groq's free-tier RPM limit
MAX_RETRIES  = int(os.getenv("MAX_RETRIES",  "2"))
BATCH_DELAY  = int(os.getenv("BATCH_DELAY",  "15"))


# ── Single company run ───────────────────────────────────────────────────────

def run_single(company: str) -> None:
    print(f"\nStarting research on: {company}")
    print("=" * 50)

    result, saved_paths = run_crew(company, max_retries=MAX_RETRIES)

    print(f"\n{'=' * 50}")
    print(f"Report saved → {saved_paths['md']}")
    print(f"JSON saved  → {saved_paths['json']}")
    print(f"\n{result}")


# ── Batch company run (Feature I) ────────────────────────────────────────────

def run_batch(csv_path: str) -> None:
    """
    Reads a CSV with a 'company' column (or a plain single-column file)
    and generates an intelligence report for every company, one at a time.

    Example CSV format (with header):
        company
        Razorpay
        Zepto
        Notion

    Plain format (no header, one company per line) also works.
    """
    if not os.path.exists(csv_path):
        print(f"[batch] Error: file not found — {csv_path}")
        sys.exit(1)

    # ── Read companies from CSV ──────────────────────────────────────────────
    companies = []
    with open(csv_path, newline="", encoding="utf-8") as f:
        sample = f.read(512)
        f.seek(0)

        # Detect if there's a header row
        has_header = "company" in sample.lower().split("\n")[0]

        reader = csv.DictReader(f) if has_header else csv.reader(f)

        for row in reader:
            if has_header:
                name = row.get("company", "").strip()
            else:
                name = row[0].strip() if row else ""
            if name:
                companies.append(name)

    if not companies:
        print("[batch] No companies found in CSV. Exiting.")
        sys.exit(1)

    total = len(companies)
    print(f"\n[batch] Found {total} companies in {csv_path}")
    print(f"[batch] Delay between runs: {BATCH_DELAY}s (set BATCH_DELAY in .env to change)")
    print("=" * 50)

    results_summary = []   # collect (company, status, paths) for final summary

    for idx, company in enumerate(companies, start=1):
        print(f"\n[{idx}/{total}] Researching: {company}")
        print("-" * 40)

        try:
            result, saved_paths = run_crew(company, max_retries=MAX_RETRIES)
            print(f"[{idx}/{total}] ✅ Done — {saved_paths['md']}")
            results_summary.append((company, "✅ success", saved_paths))
        except Exception as e:
            print(f"[{idx}/{total}] ❌ Failed — {str(e)[:120]}")
            results_summary.append((company, f"❌ failed: {str(e)[:80]}", {}))

        # Wait between companies to respect Groq free-tier rate limits
        if idx < total:
            print(f"[batch] Waiting {BATCH_DELAY}s before next company...")
            time.sleep(BATCH_DELAY)

    # ── Final summary ────────────────────────────────────────────────────────
    print(f"\n{'=' * 50}")
    print(f"[batch] Completed {total} companies\n")
    for company, status, paths in results_summary:
        print(f"  {status} — {company}")
        if paths:
            print(f"           MD:   {paths.get('md', '')}")
            print(f"           JSON: {paths.get('json', '')}")
    print("=" * 50)


# ── CLI entry point ──────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="StartupScope — AI-powered startup intelligence CLI"
    )

    mode_group = parser.add_mutually_exclusive_group()
    mode_group.add_argument(
        "--company", "-c",
        type=str,
        help="Single company name to research  (e.g. --company Razorpay)"
    )
    mode_group.add_argument(
        "--batch", "-b",
        type=str,
        metavar="CSV_PATH",
        help="Path to CSV file for batch mode  (e.g. --batch companies.csv)"
    )

    args = parser.parse_args()

    if args.batch:
        run_batch(args.batch)
    elif args.company:
        run_single(args.company)
    else:
        # Fallback: interactive prompt (original behaviour preserved)
        company = input("Enter company name to research: ").strip()
        if not company:
            print("No company entered. Exiting.")
            sys.exit(1)
        run_single(company)
