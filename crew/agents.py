import streamlit as st
import threading


st.set_page_config(
    page_title="StartupScope",
    page_icon="🔍",
    layout="wide"
)

st.markdown("""
<style>
    .stApp { background-color: #0D0D0D; color: #E0E0E0; }
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    .block-container { padding-top: 3rem; padding-bottom: 3rem; max-width: 1200px; }
    .main-title { font-size: 2.8rem; font-weight: 700; color: #FFFFFF; letter-spacing: -0.5px; margin-bottom: 0.2rem; }
    .subtitle { font-size: 1rem; color: #666666; margin-bottom: 2.5rem; letter-spacing: 0.3px; }
    .divider { border: none; border-top: 1px solid #1E1E1E; margin: 1.5rem 0; }
    .stTextInput label { color: #999999 !important; font-size: 0.85rem !important; font-weight: 500 !important; letter-spacing: 0.8px !important; text-transform: uppercase !important; }
    .stTextInput input { background-color: #141414 !important; border: 1px solid #2A2A2A !important; border-radius: 8px !important; color: #FFFFFF !important; font-size: 1rem !important; padding: 0.75rem 1rem !important; }
    .stTextInput input:focus { border-color: #444444 !important; box-shadow: none !important; }
    .stButton > button { background-color: #FFFFFF !important; color: #000000 !important; border: none !important; border-radius: 8px !important; font-weight: 600 !important; font-size: 0.95rem !important; padding: 0.6rem 2rem !important; width: 100% !important; margin-top: 0.5rem !important; }
    .stButton > button:hover { opacity: 0.85 !important; }
    .stButton > button:disabled { background-color: #2A2A2A !important; color: #555555 !important; }
    .stTabs [data-baseweb="tab-list"] { background-color: #141414 !important; border-radius: 8px !important; padding: 4px !important; border: 1px solid #2A2A2A !important; }
    .stTabs [data-baseweb="tab"] { color: #666666 !important; font-weight: 500 !important; border-radius: 6px !important; }
    .stTabs [aria-selected="true"] { background-color: #FFFFFF !important; color: #000000 !important; }
    .stMarkdown h1 { color: #FFFFFF !important; font-size: 1.5rem !important; font-weight: 700 !important; margin-top: 1.5rem !important; }
    .stMarkdown h2 { color: #CCCCCC !important; font-size: 1rem !important; font-weight: 600 !important; text-transform: uppercase !important; letter-spacing: 0.5px !important; margin-top: 1.5rem !important; padding-bottom: 0.4rem !important; border-bottom: 1px solid #1E1E1E !important; }
    .stMarkdown p, .stMarkdown li { color: #BBBBBB !important; line-height: 1.7 !important; }
    .stMarkdown strong { color: #FFFFFF !important; }
    .stDownloadButton > button { background-color: #141414 !important; color: #AAAAAA !important; border: 1px solid #2A2A2A !important; border-radius: 8px !important; font-size: 0.85rem !important; margin-top: 1rem !important; width: 100% !important; }
    .agent-step { background-color: #141414; border: 1px solid #2A2A2A; border-radius: 10px; padding: 1rem 1.2rem; margin-bottom: 0.5rem; display: flex; align-items: center; gap: 12px; }
    .agent-step-active { border-color: #FFFFFF; background-color: #1A1A1A; }
    .agent-step-done { border-color: #2A5A2A; background-color: #0F1F0F; }
    .agent-icon { font-size: 1.2rem; }
    .agent-label { font-size: 0.9rem; font-weight: 500; color: #FFFFFF; }
    .agent-desc { font-size: 0.78rem; color: #555555; }
    .badge-row { display: flex; gap: 8px; margin-bottom: 2rem; flex-wrap: wrap; }
    .badge { background-color: #141414; border: 1px solid #2A2A2A; border-radius: 20px; padding: 3px 12px; font-size: 0.75rem; color: #666666; }
    .footer-text { color: #333333; font-size: 0.78rem; text-align: center; margin-top: 3rem; letter-spacing: 0.5px; }
    .vs-divider { display: flex; align-items: center; justify-content: center; font-size: 1.2rem; font-weight: 700; color: #444444; padding-top: 1.8rem; }
    .stProgress > div > div { background-color: #FFFFFF !important; }
    .stProgress { background-color: #1E1E1E !important; border-radius: 4px !important; }
</style>
""", unsafe_allow_html=True)

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

# Mode selector
mode = st.radio(
    "Mode",
    ["Single Company", "Compare Two Companies"],
    horizontal=True,
    label_visibility="collapsed"
)

st.markdown('<hr class="divider">', unsafe_allow_html=True)

def show_progress(status_placeholder, progress_placeholder, step):
    steps = [
        ("🔍", "Researcher", "Searching the web for company data...", 0.33),
        ("📊", "Analyst", "Analyzing data and extracting insights...", 0.66),
        ("✍️", "Writer", "Writing the intelligence report...", 1.0),
    ]
    with status_placeholder.container():
        for i, (icon, label, desc, _) in enumerate(steps):
            if i < step:
                st.markdown(f"""
                <div class="agent-step agent-step-done">
                    <span class="agent-icon">✅</span>
                    <div>
                        <div class="agent-label">{label}</div>
                        <div class="agent-desc">Complete</div>
                    </div>
                </div>""", unsafe_allow_html=True)
            elif i == step:
                st.markdown(f"""
                <div class="agent-step agent-step-active">
                    <span class="agent-icon">{icon}</span>
                    <div>
                        <div class="agent-label">{label} — Working...</div>
                        <div class="agent-desc">{desc}</div>
                    </div>
                </div>""", unsafe_allow_html=True)
            else:
                st.markdown(f"""
                <div class="agent-step">
                    <span class="agent-icon">{icon}</span>
                    <div>
                        <div class="agent-label" style="color:#444">{label}</div>
                        <div class="agent-desc">Waiting...</div>
                    </div>
                </div>""", unsafe_allow_html=True)
    progress_placeholder.progress(steps[step][3])

# ── SINGLE MODE ──
if mode == "Single Company":
    company_name = st.text_input("Company", placeholder="e.g. Zepto, Razorpay, Notion, OpenAI...")

    if st.button("Generate Intelligence Report", disabled=not company_name):
        status_placeholder = st.empty()
        progress_placeholder = st.empty()

        show_progress(status_placeholder, progress_placeholder, 0)

        result = [None]
        error = [None]

        def run():
            try:
                result[0] = run_crew(company_name)
            except Exception as e:
                error[0] = str(e)

        thread = threading.Thread(target=run)
        thread.start()

        import time
        elapsed = 0
        step = 0
        while thread.is_alive():
            time.sleep(1)
            elapsed += 1
            if elapsed < 30:
                step = 0
            elif elapsed < 60:
                step = 1
            else:
                step = 2
            show_progress(status_placeholder, progress_placeholder, step)

        thread.join()

        status_placeholder.empty()
        progress_placeholder.empty()

        if error[0]:
            st.error(f"Something went wrong: {error[0]}")
            st.info("Check your API keys and try again.")
        else:
            report, saved_path = result[0]
            st.success("Report complete")
            st.markdown('<hr class="divider">', unsafe_allow_html=True)
            st.markdown(report)
            st.markdown('<hr class="divider">', unsafe_allow_html=True)
            st.download_button(
                label="↓ Download Report (.md)",
                data=report,
                file_name=f"{company_name.lower().replace(' ', '_')}_report.md",
                mime="text/markdown"
            )

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
            status_a = st.empty()
            progress_a = st.empty()
            show_progress(status_a, progress_a, 0)
            try:
                result_a, _ = run_crew(company_a)
                status_a.empty()
                progress_a.empty()
                st.success(f"{company_a} done")
            except Exception as e:
                status_a.empty()
                progress_a.empty()
                st.error(f"{company_a} failed: {str(e)}")

        with col_b:
            status_b = st.empty()
            progress_b = st.empty()
            show_progress(status_b, progress_b, 0)
            try:
                result_b, _ = run_crew(company_b)
                status_b.empty()
                progress_b.empty()
                st.success(f"{company_b} done")
            except Exception as e:
                status_b.empty()
                progress_b.empty()
                st.error(f"{company_b} failed: {str(e)}")

        if result_a and result_b:
            st.markdown('<hr class="divider">', unsafe_allow_html=True)
            tab1, tab2, tab3 = st.tabs([f"📊 {company_a}", f"📊 {company_b}", "⚡ Side by Side"])

            with tab1:
                st.markdown(result_a)
                st.download_button(label=f"↓ Download {company_a} Report", data=result_a, file_name=f"{company_a.lower().replace(' ', '_')}_report.md", mime="text/markdown", key="dl_a")

            with tab2:
                st.markdown(result_b)
                st.download_button(label=f"↓ Download {company_b} Report", data=result_b, file_name=f"{company_b.lower().replace(' ', '_')}_report.md", mime="text/markdown", key="dl_b")

            with tab3:
                col_left, col_right = st.columns(2)
                with col_left:
                    st.markdown(f"### {company_a}")
                    st.markdown(result_a)
                with col_right:
                    st.markdown(f"### {company_b}")
                    st.markdown(result_b)
                combined = f"# Comparison: {company_a} vs {company_b}\n\n---\n\n## {company_a}\n\n{result_a}\n\n---\n\n## {company_b}\n\n{result_b}"
                st.download_button(label="↓ Download Full Comparison Report", data=combined, file_name=f"comparison_report.md", mime="text/markdown", key="dl_combined")

st.markdown('<div class="footer-text">STARTUPSCOPE &nbsp;·&nbsp; CREWAI &nbsp;·&nbsp; GROQ &nbsp;·&nbsp; STREAMLIT</div>', unsafe_allow_html=True)