import streamlit as st
from crew.crew import run_crew
from pathlib import Path

st.set_page_config(
    page_title="StartupScope",
    page_icon="🔍",
    layout="centered"
)

st.markdown("""
<style>
    .stApp { background-color: #0D0D0D; color: #E0E0E0; }
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}

    .block-container { padding-top: 3rem; padding-bottom: 3rem; max-width: 760px; }

    .main-title { font-size: 2.8rem; font-weight: 700; color: #FFFFFF; letter-spacing: -0.5px; margin-bottom: 0.2rem; }
    .subtitle { font-size: 1rem; color: #666666; margin-bottom: 2.5rem; letter-spacing: 0.3px; }
    .divider { border: none; border-top: 1px solid #1E1E1E; margin: 1.5rem 0; }

    .stTextInput label { color: #999999 !important; font-size: 0.85rem !important; font-weight: 500 !important; letter-spacing: 0.8px !important; text-transform: uppercase !important; }
    .stTextInput input { background-color: #141414 !important; border: 1px solid #2A2A2A !important; border-radius: 8px !important; color: #FFFFFF !important; font-size: 1rem !important; padding: 0.75rem 1rem !important; }
    .stTextInput input:focus { border-color: #444444 !important; box-shadow: none !important; }

    .stSelectbox label { color: #999999 !important; font-size: 0.85rem !important; font-weight: 500 !important; letter-spacing: 0.8px !important; text-transform: uppercase !important; }
    .stSelectbox > div > div { background-color: #141414 !important; border: 1px solid #2A2A2A !important; border-radius: 8px !important; color: #FFFFFF !important; }

    .stRadio label { color: #999999 !important; font-size: 0.85rem !important; font-weight: 500 !important; letter-spacing: 0.8px !important; text-transform: uppercase !important; }
    .stRadio div[role="radiogroup"] label { color: #AAAAAA !important; font-size: 0.9rem !important; text-transform: none !important; letter-spacing: 0 !important; }

    .stButton > button { background-color: #FFFFFF !important; color: #000000 !important; border: none !important; border-radius: 8px !important; font-weight: 600 !important; font-size: 0.95rem !important; padding: 0.6rem 2rem !important; width: 100% !important; margin-top: 0.5rem !important; transition: opacity 0.2s !important; }
    .stButton > button:hover { opacity: 0.85 !important; }
    .stButton > button:disabled { background-color: #2A2A2A !important; color: #555555 !important; }

    .stProgress > div > div { background-color: #FFFFFF !important; }
    .stProgress { background-color: #1E1E1E !important; border-radius: 8px !important; }

    .stSuccess { background-color: #0F1F0F !important; border: 1px solid #1A3A1A !important; border-radius: 8px !important; color: #4CAF50 !important; }
    .stAlert { background-color: #1A0F0F !important; border: 1px solid #3A1A1A !important; border-radius: 8px !important; }

    .stMarkdown h1 { color: #FFFFFF !important; font-size: 1.8rem !important; font-weight: 700 !important; margin-top: 2rem !important; }
    .stMarkdown h2 { color: #CCCCCC !important; font-size: 1.1rem !important; font-weight: 600 !important; text-transform: uppercase !important; letter-spacing: 0.5px !important; margin-top: 1.8rem !important; padding-bottom: 0.4rem !important; border-bottom: 1px solid #1E1E1E !important; }
    .stMarkdown p, .stMarkdown li { color: #BBBBBB !important; line-height: 1.7 !important; }
    .stMarkdown strong { color: #FFFFFF !important; }

    .stDownloadButton > button { background-color: #141414 !important; color: #AAAAAA !important; border: 1px solid #2A2A2A !important; border-radius: 8px !important; font-size: 0.85rem !important; margin-top: 0.5rem !important; width: 100% !important; }
    .stSpinner > div { border-top-color: #FFFFFF !important; }

    .footer-text { color: #333333; font-size: 0.78rem; text-align: center; margin-top: 3rem; letter-spacing: 0.5px; }

    .badge-row { display: flex; gap: 8px; margin-bottom: 2rem; flex-wrap: wrap; }
    .badge { background-color: #141414; border: 1px solid #2A2A2A; border-radius: 20px; padding: 3px 12px; font-size: 0.75rem; color: #666666; }

    section[data-testid="stSidebar"] { background-color: #0A0A0A !important; border-right: 1px solid #1E1E1E !important; }
    section[data-testid="stSidebar"] .stButton > button { background-color: #141414 !important; color: #AAAAAA !important; border: 1px solid #2A2A2A !important; font-size: 0.82rem !important; font-weight: 400 !important; text-align: left !important; padding: 0.5rem 0.75rem !important; margin-top: 0.2rem !important; }
    section[data-testid="stSidebar"] .stButton > button:hover { background-color: #1E1E1E !important; color: #FFFFFF !important; opacity: 1 !important; }
</style>
""", unsafe_allow_html=True)


# ── Sidebar: report history ───────────────────────────────
def load_report_history():
    outputs_dir = Path("outputs")
    if not outputs_dir.exists():
        return []
    files = sorted(outputs_dir.glob("*.md"), key=lambda f: f.stat().st_mtime, reverse=True)
    return files

def format_report_name(filepath: Path) -> str:
    name = filepath.stem
    # Strip timestamp suffix (last 16 chars: _YYYYMMDD_HHMMSS)
    if len(name) > 16 and name[-7].isdigit() and name[-15] == "_":
        name = name[:-16]
    return name.replace("_", " ").title()

with st.sidebar:
    st.markdown("### Past Reports")
    history = load_report_history()

    if not history:
        st.caption("No reports yet. Generate your first one.")
    else:
        st.caption(f"{len(history)} report{'s' if len(history) != 1 else ''} saved")
        st.markdown("---")
        for report_file in history:
            label = format_report_name(report_file)
            if st.button(label, key=str(report_file)):
                st.session_state["loaded_report"] = report_file.read_text(encoding="utf-8")
                st.session_state["loaded_report_name"] = label

    st.markdown("---")
    if st.button("Clear history", key="clear_history"):
        for f in load_report_history():
            f.unlink()
        st.session_state.pop("loaded_report", None)
        st.session_state.pop("loaded_report_name", None)
        st.rerun()


# ── Header ────────────────────────────────────────────────
st.markdown('<div class="main-title">StartupScope</div>', unsafe_allow_html=True)
st.markdown('<div class="subtitle">AI-powered startup intelligence. Research any company in 90 seconds.</div>', unsafe_allow_html=True)

st.markdown("""
<div class="badge-row">
    <span class="badge">CrewAI</span>
    <span class="badge">LangChain</span>
    <span class="badge">Groq · LLaMA 3</span>
    <span class="badge">Live Web Search</span>
    <span class="badge">Multi-Agent</span>
</div>
""", unsafe_allow_html=True)

st.markdown('<hr class="divider">', unsafe_allow_html=True)


# ── If a past report was loaded from sidebar ──────────────
if "loaded_report" in st.session_state:
    st.info(f"Showing saved report: **{st.session_state['loaded_report_name']}**")
    st.markdown('<hr class="divider">', unsafe_allow_html=True)
    st.markdown(st.session_state["loaded_report"])
    st.markdown('<hr class="divider">', unsafe_allow_html=True)

    dl1, dl2 = st.columns(2)
    with dl1:
        st.download_button(
            label="↓ Download (.md)",
            data=st.session_state["loaded_report"],
            file_name=f"{st.session_state['loaded_report_name'].lower().replace(' ', '_')}_report.md",
            mime="text/markdown"
        )
    with dl2:
        if st.button("✕ Close report"):
            st.session_state.pop("loaded_report", None)
            st.session_state.pop("loaded_report_name", None)
            st.rerun()

    st.markdown('<hr class="divider">', unsafe_allow_html=True)


# ── Input ─────────────────────────────────────────────────
company_name = st.text_input(
    "Company",
    placeholder="e.g. Zepto, Razorpay, Notion, OpenAI...",
    label_visibility="visible"
)

col1, col2 = st.columns(2)
with col1:
    model_choice = st.selectbox(
        "Model",
        ["llama3-70b-8192", "llama3-8b-8192", "mixtral-8x7b-32768"],
        help="70b = most accurate · 8b = faster"
    )
with col2:
    depth_choice = st.radio(
        "Depth",
        ["Quick", "Deep"],
        horizontal=True,
        help="Quick = 3 searches · Deep = 7 searches"
    )

st.markdown('<hr class="divider">', unsafe_allow_html=True)


# ── Generate ──────────────────────────────────────────────
if st.button("Generate Intelligence Report", disabled=not company_name):
    progress = st.progress(0, text="Starting agents...")

    with st.spinner(f"Researching {company_name}..."):
        try:
            progress.progress(15, text="Researcher agent: searching the web...")
            result, saved_path = run_crew(company_name, model=model_choice, depth=depth_choice)
            progress.progress(100, text="Complete.")

            st.session_state["loaded_report"] = result
            st.session_state["loaded_report_name"] = company_name.title()

            st.success("Report complete")
            st.markdown('<hr class="divider">', unsafe_allow_html=True)
            st.markdown(result)
            st.markdown('<hr class="divider">', unsafe_allow_html=True)

            dl1, dl2 = st.columns(2)
            with dl1:
                st.download_button(
                    label="↓ Download (.md)",
                    data=result,
                    file_name=f"{company_name.lower().replace(' ', '_')}_report.md",
                    mime="text/markdown"
                )
            with dl2:
                st.download_button(
                    label="↓ Download (.txt)",
                    data=result,
                    file_name=f"{company_name.lower().replace(' ', '_')}_report.txt",
                    mime="text/plain"
                )

        except Exception as e:
            st.error(f"Something went wrong: {str(e)}")
            st.info("Check your API keys and try again.")


# ── Footer ────────────────────────────────────────────────
st.markdown("""
<div class="footer-text">
    STARTUPSCOPE &nbsp;·&nbsp; CREWAI &nbsp;·&nbsp; GROQ &nbsp;·&nbsp; STREAMLIT
</div>
""", unsafe_allow_html=True)