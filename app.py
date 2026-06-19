import streamlit as st
from crew.crew import run_crew
from history import load_history, add_entry, clear_history
from theme import inject_theme

st.set_page_config(
    page_title="StartupScope",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ── THEME BOOTSTRAP ──
# Must happen before any other st.markdown / UI calls.
if "theme_mode" not in st.session_state:
    st.session_state.theme_mode = "Brief"   # default: dark

inject_theme(st.session_state.theme_mode)

# ── SESSION STATE ──
if "viewing_history_id" not in st.session_state:
    st.session_state.viewing_history_id = None

# ── SIDEBAR: REPORT HISTORY ──
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

# ── HEADER ROW (title left, theme toggle right) ──
header_left, header_right = st.columns([8, 2])

with header_left:
    st.markdown('<div class="main-title">StartupScope</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="subtitle">AI-powered startup intelligence. '
        'Research any company in 90 seconds.</div>',
        unsafe_allow_html=True
    )

with header_right:
    # Spacer so the toggle sits roughly level with the title baseline
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
        st.rerun()   # re-render with new palette injected at top

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

# ── HISTORY VIEW ──
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

# ── MODE SELECTOR ──
mode = st.radio(
    "Mode",
    ["Single Company", "Compare Two Companies"],
    horizontal=True,
    label_visibility="collapsed"
)

st.markdown('<hr class="divider">', unsafe_allow_html=True)

# ── SINGLE MODE ──
if mode == "Single Company":
    company_name = st.text_input(
        "Company",
        placeholder="e.g. Zepto, Razorpay, Notion, OpenAI..."
    )

    if st.button("Generate Intelligence Report", disabled=not company_name):
        with st.spinner(f"Researching {company_name}… agents working in sequence"):
            try:
                result, saved_path = run_crew(company_name)
                add_entry(company_name, result, mode="single")
                st.success("Report complete")
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

# ── COMPARE MODE ──
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

        col_a, col_b = st.columns(2)

        with col_a:
            with st.spinner(f"Researching {company_a}..."):
                try:
                    result_a, _ = run_crew(company_a)
                    st.success(f"{company_a} done")
                except Exception as e:
                    st.error(f"{company_a} failed: {str(e)}")

        with col_b:
            with st.spinner(f"Researching {company_b}..."):
                try:
                    result_b, _ = run_crew(company_b)
                    st.success(f"{company_b} done")
                except Exception as e:
                    st.error(f"{company_b} failed: {str(e)}")

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

# ── FOOTER ──
st.markdown("""
<div class="footer-text">
    STARTUPSCOPE &nbsp;·&nbsp; CREWAI &nbsp;·&nbsp; GROQ &nbsp;·&nbsp; STREAMLIT
</div>
""", unsafe_allow_html=True)