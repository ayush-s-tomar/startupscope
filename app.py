import streamlit as st
from crew.crew import run_crew
from history import load_history, add_entry, clear_history

st.set_page_config(
    page_title="StartupScope",
    page_icon="🔍",
    layout="wide"
)

st.markdown("""
<style>
    .stApp {
        background-color: #0D0D0D;
        color: #E0E0E0;
    }
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    .block-container {
        padding-top: 3rem;
        padding-bottom: 3rem;
        max-width: 1200px;
    }
    .main-title {
        font-size: 2.8rem;
        font-weight: 700;
        color: #FFFFFF;
        letter-spacing: -0.5px;
        margin-bottom: 0.2rem;
    }
    .subtitle {
        font-size: 1rem;
        color: #666666;
        margin-bottom: 2.5rem;
        letter-spacing: 0.3px;
    }
    .divider {
        border: none;
        border-top: 1px solid #1E1E1E;
        margin: 1.5rem 0;
    }
    .stTextInput label {
        color: #999999 !important;
        font-size: 0.85rem !important;
        font-weight: 500 !important;
        letter-spacing: 0.8px !important;
        text-transform: uppercase !important;
    }
    .stTextInput input {
        background-color: #141414 !important;
        border: 1px solid #2A2A2A !important;
        border-radius: 8px !important;
        color: #FFFFFF !important;
        font-size: 1rem !important;
        padding: 0.75rem 1rem !important;
    }
    .stTextInput input:focus {
        border-color: #444444 !important;
        box-shadow: none !important;
    }
    .stButton > button {
        background-color: #FFFFFF !important;
        color: #000000 !important;
        border: none !important;
        border-radius: 8px !important;
        font-weight: 600 !important;
        font-size: 0.95rem !important;
        padding: 0.6rem 2rem !important;
        width: 100% !important;
        margin-top: 0.5rem !important;
        transition: opacity 0.2s !important;
    }
    .stButton > button:hover {
        opacity: 0.85 !important;
    }
    .stButton > button:disabled {
        background-color: #2A2A2A !important;
        color: #555555 !important;
    }
    .stTabs [data-baseweb="tab-list"] {
        background-color: #141414 !important;
        border-radius: 8px !important;
        padding: 4px !important;
        border: 1px solid #2A2A2A !important;
    }
    .stTabs [data-baseweb="tab"] {
        color: #666666 !important;
        font-weight: 500 !important;
        border-radius: 6px !important;
    }
    .stTabs [aria-selected="true"] {
        background-color: #FFFFFF !important;
        color: #000000 !important;
    }
    .stMarkdown h1 {
        color: #FFFFFF !important;
        font-size: 1.5rem !important;
        font-weight: 700 !important;
        margin-top: 1.5rem !important;
    }
    .stMarkdown h2 {
        color: #CCCCCC !important;
        font-size: 1rem !important;
        font-weight: 600 !important;
        text-transform: uppercase !important;
        letter-spacing: 0.5px !important;
        margin-top: 1.5rem !important;
        padding-bottom: 0.4rem !important;
        border-bottom: 1px solid #1E1E1E !important;
    }
    .stMarkdown p, .stMarkdown li {
        color: #BBBBBB !important;
        line-height: 1.7 !important;
    }
    .stMarkdown strong {
        color: #FFFFFF !important;
    }
    .stDownloadButton > button {
        background-color: #141414 !important;
        color: #AAAAAA !important;
        border: 1px solid #2A2A2A !important;
        border-radius: 8px !important;
        font-size: 0.85rem !important;
        margin-top: 1rem !important;
        width: 100% !important;
    }
    .mode-card {
        background-color: #141414;
        border: 1px solid #2A2A2A;
        border-radius: 10px;
        padding: 1.2rem 1.5rem;
        cursor: pointer;
        margin-bottom: 1rem;
    }
    .mode-card-active {
        border-color: #FFFFFF;
    }
    .mode-title {
        font-size: 1rem;
        font-weight: 600;
        color: #FFFFFF;
        margin-bottom: 0.2rem;
    }
    .mode-desc {
        font-size: 0.82rem;
        color: #666666;
    }
    .badge-row {
        display: flex;
        gap: 8px;
        margin-bottom: 2rem;
        flex-wrap: wrap;
    }
    .badge {
        background-color: #141414;
        border: 1px solid #2A2A2A;
        border-radius: 20px;
        padding: 3px 12px;
        font-size: 0.75rem;
        color: #666666;
    }
    .footer-text {
        color: #333333;
        font-size: 0.78rem;
        text-align: center;
        margin-top: 3rem;
        letter-spacing: 0.5px;
    }
    .vs-divider {
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 1.2rem;
        font-weight: 700;
        color: #444444;
        padding-top: 1.8rem;
    }
    .history-item {
        background-color: #141414;
        border: 1px solid #2A2A2A;
        border-radius: 8px;
        padding: 0.6rem 0.8rem;
        margin-bottom: 0.5rem;
    }
    .history-company {
        color: #FFFFFF;
        font-size: 0.88rem;
        font-weight: 600;
    }
    .history-time {
        color: #666666;
        font-size: 0.72rem;
        margin-top: 0.1rem;
    }
    section[data-testid="stSidebar"] {
        background-color: #0A0A0A !important;
        border-right: 1px solid #1E1E1E !important;
    }
    section[data-testid="stSidebar"] .stButton > button {
        background-color: #141414 !important;
        color: #BBBBBB !important;
        border: 1px solid #2A2A2A !important;
        font-weight: 500 !important;
        font-size: 0.8rem !important;
        padding: 0.4rem 0.8rem !important;
    }
</style>
""", unsafe_allow_html=True)

# Session state for viewing a history entry
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
            label = entry["label"]
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

# Header
st.markdown('<div class="main-title">StartupScope</div>', unsafe_allow_html=True)
st.markdown('<div class="subtitle">AI-powered startup intelligence. Research any company in 90 seconds.</div>', unsafe_allow_html=True)

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

# ── IF VIEWING A HISTORY ENTRY, SHOW IT AND STOP ──
if st.session_state.viewing_history_id:
    history = load_history()
    selected = next((e for e in history if e["id"] == st.session_state.viewing_history_id), None)

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

# Mode selector
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
        with st.spinner(f"Researching {company_name}... agents working in sequence"):
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
            combined = f"# Comparison: {company_a} vs {company_b}\n\n---\n\n## {company_a}\n\n{result_a}\n\n---\n\n## {company_b}\n\n{result_b}"
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

# Footer
st.markdown("""
<div class="footer-text">
    STARTUPSCOPE &nbsp;·&nbsp; CREWAI &nbsp;·&nbsp; GROQ &nbsp;·&nbsp; STREAMLIT
</div>
""", unsafe_allow_html=True)