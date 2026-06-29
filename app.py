import streamlit as st
from crew.crew import run_crew
from history import load_history, add_entry, clear_history
from theme import inject_theme
import threading
import queue
import time

st.set_page_config(
    page_title="StartupScope",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ── THEME BOOTSTRAP ──
if "theme_mode" not in st.session_state:
    st.session_state.theme_mode = "Brief"

inject_theme(st.session_state.theme_mode)

# ── SESSION STATE ──
if "viewing_history_id" not in st.session_state:
    st.session_state.viewing_history_id = None


# ── LIVE PROGRESS RUNNER ────────────────────────────────────────────────────

# Each step: (display label, estimated seconds it takes)
_STEPS = [
    ("🔍 Researcher is searching the web...",        30),
    ("📊 Analyst is extracting insights...",          20),
    ("✍️  Writer is composing the report...",         15),
    ("✅ Finalising and formatting output...",          5),
]

def _run_in_thread(company_name: str, result_queue: queue.Queue) -> None:
    """Run crew in a background thread, push result or exception into queue."""
    try:
        result, path = run_crew(company_name)
        result_queue.put(("ok", result))
    except Exception as e:
        result_queue.put(("err", str(e)))


def run_with_progress(company_name: str) -> str:
    """
    Runs the crew in a background thread while showing a live step-by-step
    progress UI in Streamlit. Returns the report string on success.
    Raises RuntimeError on failure.
    """
    result_queue = queue.Queue()
    thread = threading.Thread(
        target=_run_in_thread,
        args=(company_name, result_queue),
        daemon=True
    )
    thread.start()

    # ── Progress UI ─────────────────────────────────────────────────────────
    progress_bar   = st.progress(0)
    status_text    = st.empty()
    step_container = st.empty()

    total_steps    = len(_STEPS)
    step_idx       = 0
    elapsed        = 0
    step_elapsed   = 0

    while thread.is_alive() or not result_queue.empty():
        # Rotate through steps based on elapsed time
        if step_idx < total_steps:
            label, duration = _STEPS[step_idx]
            status_text.markdown(f"**{label}**")

            # Progress within current step
            step_pct = min(step_elapsed / duration, 1.0)
            overall_pct = (step_idx + step_pct) / total_steps
            progress_bar.progress(min(overall_pct, 0.95))  # cap at 95 until done

            # Animated dots to show liveness
            dots = "." * ((elapsed % 4) + 1)
            step_container.caption(
                f"Step {step_idx + 1}/{total_steps} · "
                f"{int(step_elapsed)}s elapsed{dots}"
            )

            step_elapsed += 0.5
            if step_elapsed >= duration and step_idx < total_steps - 1:
                step_idx    += 1
                step_elapsed = 0

        time.sleep(0.5)
        elapsed += 0.5

        # Check if result is ready early
        if not result_queue.empty():
            break

    # ── Collect result ───────────────────────────────────────────────────────
    progress_bar.progress(1.0)
    status_text.empty()
    step_container.empty()
    progress_bar.empty()

    try:
        status, payload = result_queue.get(timeout=5)
    except queue.Empty:
        raise RuntimeError("Crew timed out — no result received.")

    if status == "err":
        raise RuntimeError(payload)
    return payload


# ── SIDEBAR: REPORT HISTORY ──────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### 📜 Report History")
    history = load_history()

    if not history:
        st.caption("No reports generated yet. Your past reports will show up here.")
    else:
        if st.button("🏠 New Search", use_container_width=True):
            st.session_state.viewing_history_id = None
            st.rerun()

        st.markdown('<hr class="divider">', unsafe_allow_html=True)

        for entry in history:
            label    = entry["label"]
            time_str = entry["display_time"]
            mode_tag = "⚡ Compare" if entry["mode"] == "compare" else "🔍 Single"

            st.markdown(f"""
            <div class="history-item">
                <div class="history-company">{label}</div>
                <div class="history-time">{mode_tag} · {time_str}</div>
            </div>
            """, unsafe_allow_html=True)

            if st.button("View", key=f"view_{entry['id']}", use_container_width=True):
                st.session_state.viewing_history_id = entry["id"]
                st.rerun()

        st.markdown('<hr class="divider">', unsafe_allow_html=True)
        if st.button("🗑️ Clear History", use_container_width=True):
            clear_history()
            st.session_state.viewing_history_id = None
            st.rerun()


# ── HEADER ───────────────────────────────────────────────────────────────────
header_left, header_right = st.columns([8, 2])

with header_left:
    st.markdown('<div class="main-title">StartupScope</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="subtitle">AI-powered startup intelligence. '
        'Research any company in 90 seconds.</div>',
        unsafe_allow_html=True
    )

with header_right:
    st.markdown("<br>", unsafe_allow_html=True)
    chosen = st.radio(
        "Theme",
        ["Brief", "Console"],
        index=0 if st.session_state.theme_mode == "Brief" else 1,
        horizontal=True,
        label_visibility="collapsed",
        key="theme_radio"
    )
    if chosen != st.session_state.theme_mode:
        st.session_state.theme_mode = chosen
        st.rerun()

st.markdown("""
<div class="badge-row">
    <span class="badge">CrewAI</span>
    <span class="badge">LangChain</span>
    <span class="badge">Groq · LLaMA 3.3</span>
    <span class="badge">Live Web Search</span>
    <span class="badge">Multi-Agent</span>
</div>
""", unsafe_allow_html=True)

st.markdown('<hr class="divider">', unsafe_allow_html=True)


# ── HISTORY VIEW ─────────────────────────────────────────────────────────────
if st.session_state.viewing_history_id:
    history  = load_history()
    selected = next(
        (e for e in history if e["id"] == st.session_state.viewing_history_id),
        None
    )

    if selected:
        st.markdown(f"**Viewing saved report** · {selected['display_time']}")
        st.markdown('<hr class="divider">', unsafe_allow_html=True)
        st.markdown(selected["content"])
        st.markdown('<hr class="divider">', unsafe_allow_html=True)
        st.download_button(
            label="↓ Download Report (.md)",
            data=selected["content"],
            file_name=f"{selected['company'].lower().replace(' ', '_')}_report.md",
            mime="text/markdown"
        )
    else:
        st.warning("That report could not be found. It may have been cleared.")

    st.markdown("""
    <div class="footer-text">
        STARTUPSCOPE &nbsp;·&nbsp; CREWAI &nbsp;·&nbsp; GROQ &nbsp;·&nbsp; STREAMLIT
    </div>
    """, unsafe_allow_html=True)
    st.stop()


# ── MODE SELECTOR ─────────────────────────────────────────────────────────────
mode = st.radio(
    "Mode",
    ["Single Company", "Compare Two Companies"],
    horizontal=True,
    label_visibility="collapsed"
)

st.markdown('<hr class="divider">', unsafe_allow_html=True)


# ── SINGLE MODE ───────────────────────────────────────────────────────────────
if mode == "Single Company":
    company_name = st.text_input(
        "Company",
        placeholder="e.g. Zepto, Razorpay, Notion, OpenAI..."
    )

    if st.button("Generate Intelligence Report", disabled=not company_name):
        try:
            # ── Live progress replaces the silent spinner ──────────────────
            result = run_with_progress(company_name)

            add_entry(company_name, result, mode="single")
            st.success("✅ Report complete")
            st.markdown('<hr class="divider">', unsafe_allow_html=True)
            st.markdown(result)
            st.markdown('<hr class="divider">', unsafe_allow_html=True)
            st.download_button(
                label="↓ Download Report (.md)",
                data=result,
                file_name=f"{company_name.lower().replace(' ', '_')}_report.md",
                mime="text/markdown"
            )
        except Exception as e:
            st.error(f"Something went wrong: {str(e)}")
            st.info("Check your API keys and try again.")


# ── COMPARE MODE ──────────────────────────────────────────────────────────────
else:
    col1, col_mid, col2 = st.columns([5, 1, 5])

    with col1:
        company_a = st.text_input("Company A", placeholder="e.g. Razorpay")

    with col_mid:
        st.markdown('<div class="vs-divider">VS</div>', unsafe_allow_html=True)

    with col2:
        company_b = st.text_input("Company B", placeholder="e.g. Paytm")

    both_filled = company_a and company_b

    if st.button("Compare Both Companies", disabled=not both_filled):
        result_a = None
        result_b = None

        # ── Company A with live progress ───────────────────────────────────
        st.markdown(f"#### Researching {company_a}...")
        try:
            result_a = run_with_progress(company_a)
            st.success(f"✅ {company_a} done")
        except Exception as e:
            st.error(f"{company_a} failed: {str(e)}")

        # ── Company B with live progress ───────────────────────────────────
        if result_a:
            st.markdown(f"#### Researching {company_b}...")
            try:
                result_b = run_with_progress(company_b)
                st.success(f"✅ {company_b} done")
            except Exception as e:
                st.error(f"{company_b} failed: {str(e)}")

        # ── Render comparison ──────────────────────────────────────────────
        if result_a and result_b:
            combined = (
                f"# Comparison: {company_a} vs {company_b}\n\n---\n\n"
                f"## {company_a}\n\n{result_a}\n\n---\n\n"
                f"## {company_b}\n\n{result_b}"
            )
            add_entry(
                f"{company_a} vs {company_b}",
                combined,
                mode="compare",
                extra_label=f"{company_a} vs {company_b}"
            )

            st.markdown('<hr class="divider">', unsafe_allow_html=True)

            tab1, tab2, tab3 = st.tabs([
                f"📊 {company_a}",
                f"📊 {company_b}",
                "⚡ Side by Side"
            ])

            with tab1:
                st.markdown(result_a)
                st.download_button(
                    label=f"↓ Download {company_a} Report",
                    data=result_a,
                    file_name=f"{company_a.lower().replace(' ', '_')}_report.md",
                    mime="text/markdown",
                    key="dl_a"
                )

            with tab2:
                st.markdown(result_b)
                st.download_button(
                    label=f"↓ Download {company_b} Report",
                    data=result_b,
                    file_name=f"{company_b.lower().replace(' ', '_')}_report.md",
                    mime="text/markdown",
                    key="dl_b"
                )

            with tab3:
                col_left, col_right = st.columns(2)
                with col_left:
                    st.markdown(f"### {company_a}")
                    st.markdown(result_a)
                with col_right:
                    st.markdown(f"### {company_b}")
                    st.markdown(result_b)

                st.download_button(
                    label="↓ Download Full Comparison Report",
                    data=combined,
                    file_name=f"{company_a.lower()}_vs_{company_b.lower()}_comparison.md",
                    mime="text/markdown",
                    key="dl_combined"
                )


# ── FOOTER ────────────────────────────────────────────────────────────────────
st.markdown("""
<div class="footer-text">
    STARTUPSCOPE &nbsp;·&nbsp; CREWAI &nbsp;·&nbsp; GROQ &nbsp;·&nbsp; STREAMLIT
</div>
""", unsafe_allow_html=True)