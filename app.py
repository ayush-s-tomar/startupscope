import streamlit as st
from crew.crew import run_crew

st.set_page_config(
    page_title="StartupScope",
    page_icon="🔍",
    layout="centered"
)

st.markdown("""
<style>
    /* Main background */
    .stApp {
        background-color: #0D0D0D;
        color: #E0E0E0;
    }

    /* Hide Streamlit branding */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}

    /* Main container */
    .block-container {
        padding-top: 3rem;
        padding-bottom: 3rem;
        max-width: 760px;
    }

    /* Title */
    .main-title {
        font-size: 2.8rem;
        font-weight: 700;
        color: #FFFFFF;
        letter-spacing: -0.5px;
        margin-bottom: 0.2rem;
    }

    /* Subtitle */
    .subtitle {
        font-size: 1rem;
        color: #666666;
        margin-bottom: 2.5rem;
        letter-spacing: 0.3px;
    }

    /* Divider */
    .divider {
        border: none;
        border-top: 1px solid #1E1E1E;
        margin: 1.5rem 0;
    }

    /* Input label */
    .stTextInput label {
        color: #999999 !important;
        font-size: 0.85rem !important;
        font-weight: 500 !important;
        letter-spacing: 0.8px !important;
        text-transform: uppercase !important;
    }

    /* Input box */
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

    /* Button */
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

    /* Success box */
    .stSuccess {
        background-color: #0F1F0F !important;
        border: 1px solid #1A3A1A !important;
        border-radius: 8px !important;
        color: #4CAF50 !important;
    }

    /* Error box */
    .stAlert {
        background-color: #1A0F0F !important;
        border: 1px solid #3A1A1A !important;
        border-radius: 8px !important;
    }

    /* Report markdown */
    .stMarkdown h1 {
        color: #FFFFFF !important;
        font-size: 1.8rem !important;
        font-weight: 700 !important;
        margin-top: 2rem !important;
    }

    .stMarkdown h2 {
        color: #CCCCCC !important;
        font-size: 1.1rem !important;
        font-weight: 600 !important;
        text-transform: uppercase !important;
        letter-spacing: 0.5px !important;
        margin-top: 1.8rem !important;
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

    /* Download button */
    .stDownloadButton > button {
        background-color: #141414 !important;
        color: #AAAAAA !important;
        border: 1px solid #2A2A2A !important;
        border-radius: 8px !important;
        font-size: 0.85rem !important;
        margin-top: 1rem !important;
        width: 100% !important;
    }

    /* Spinner */
    .stSpinner > div {
        border-top-color: #FFFFFF !important;
    }

    /* Footer text */
    .footer-text {
        color: #333333;
        font-size: 0.78rem;
        text-align: center;
        margin-top: 3rem;
        letter-spacing: 0.5px;
    }

    /* Badge row */
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
</style>
""", unsafe_allow_html=True)

# Header
st.markdown('<div class="main-title">StartupScope</div>', unsafe_allow_html=True)
st.markdown('<div class="subtitle">AI-powered startup intelligence. Research any company in 90 seconds.</div>', unsafe_allow_html=True)

# Badges
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

# Input
company_name = st.text_input(
    "Company",
    placeholder="e.g. Zepto, Razorpay, Notion, OpenAI...",
    label_visibility="visible"
)

# Button
if st.button("Generate Intelligence Report", disabled=not company_name):
    with st.spinner(f"Researching {company_name}... agents working in sequence"):
        try:
            result, saved_path = run_crew(company_name)
            st.success(f"Report complete")
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

# Footer
st.markdown("""
<div class="footer-text">
    STARTUPSCOPE &nbsp;·&nbsp; CREWAI &nbsp;·&nbsp; GROQ &nbsp;·&nbsp; STREAMLIT
</div>
""", unsafe_allow_html=True)
