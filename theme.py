"""
StartupScope theme system.

Two modes, one variable contract:
  --bg        page background
  --panel     card / input surface
  --panel-alt sidebar background
  --ink       primary text
  --ink-dim   secondary / muted text
  --ink-faint caption / placeholder text
  --accent    interactive highlight (button fill, active tab)
  --on-accent text on top of --accent
  --hairline  border / divider colour
"""

BRIEF_CSS = """
:root {
    --bg:        #0D0D0D;
    --panel:     #141414;
    --panel-alt: #0A0A0A;
    --ink:       #FFFFFF;
    --ink-dim:   #BBBBBB;
    --ink-faint: #666666;
    --accent:    #FFFFFF;
    --on-accent: #000000;
    --hairline:  #1E1E1E;
    --panel-border: #2A2A2A;
}
"""

CONSOLE_CSS = """
:root {
    --bg:        #F5F4F0;
    --panel:     #FFFFFF;
    --panel-alt: #EEEDE9;
    --ink:       #111111;
    --ink-dim:   #444444;
    --ink-faint: #888888;
    --accent:    #111111;
    --on-accent: #FFFFFF;
    --hairline:  #DEDBD4;
    --panel-border: #D4D1CB;
}
"""

SHARED_CSS = """
    .stApp {
        background-color: var(--bg) !important;
        color: var(--ink-dim) !important;
    }
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    .block-container {
        padding-top: 3rem;
        padding-bottom: 3rem;
        max-width: 1200px;
    }

    /* ── Typography ── */
    .main-title {
        font-size: 2.8rem;
        font-weight: 700;
        color: var(--ink);
        letter-spacing: -0.5px;
        margin-bottom: 0.2rem;
    }
    .subtitle {
        font-size: 1rem;
        color: var(--ink-faint);
        margin-bottom: 2.5rem;
        letter-spacing: 0.3px;
    }
    .divider {
        border: none;
        border-top: 1px solid var(--hairline);
        margin: 1.5rem 0;
    }

    /* ── Inputs ── */
    .stTextInput label {
        color: var(--ink-faint) !important;
        font-size: 0.85rem !important;
        font-weight: 500 !important;
        letter-spacing: 0.8px !important;
        text-transform: uppercase !important;
    }
    .stTextInput input {
        background-color: var(--panel) !important;
        border: 1px solid var(--panel-border) !important;
        border-radius: 8px !important;
        color: var(--ink) !important;
        font-size: 1rem !important;
        padding: 0.75rem 1rem !important;
    }
    .stTextInput input:focus {
        border-color: var(--ink-dim) !important;
        box-shadow: none !important;
    }

    /* ── Primary button ── */
    .stButton > button {
        background-color: var(--accent) !important;
        color: var(--on-accent) !important;
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
        background-color: var(--panel-border) !important;
        color: var(--ink-faint) !important;
    }

    /* ── Tabs ── */
    .stTabs [data-baseweb="tab-list"] {
        background-color: var(--panel) !important;
        border-radius: 8px !important;
        padding: 4px !important;
        border: 1px solid var(--panel-border) !important;
    }
    .stTabs [data-baseweb="tab"] {
        color: var(--ink-faint) !important;
        font-weight: 500 !important;
        border-radius: 6px !important;
    }
    .stTabs [aria-selected="true"] {
        background-color: var(--accent) !important;
        color: var(--on-accent) !important;
    }

    /* ── Markdown content ── */
    .stMarkdown h1 {
        color: var(--ink) !important;
        font-size: 1.5rem !important;
        font-weight: 700 !important;
        margin-top: 1.5rem !important;
    }
    .stMarkdown h2 {
        color: var(--ink-dim) !important;
        font-size: 1rem !important;
        font-weight: 600 !important;
        text-transform: uppercase !important;
        letter-spacing: 0.5px !important;
        margin-top: 1.5rem !important;
        padding-bottom: 0.4rem !important;
        border-bottom: 1px solid var(--hairline) !important;
    }
    .stMarkdown p, .stMarkdown li {
        color: var(--ink-dim) !important;
        line-height: 1.7 !important;
    }
    .stMarkdown strong {
        color: var(--ink) !important;
    }

    /* ── Download button ── */
    .stDownloadButton > button {
        background-color: var(--panel) !important;
        color: var(--ink-dim) !important;
        border: 1px solid var(--panel-border) !important;
        border-radius: 8px !important;
        font-size: 0.85rem !important;
        margin-top: 1rem !important;
        width: 100% !important;
    }

    /* ── Custom component classes ── */
    .mode-card {
        background-color: var(--panel);
        border: 1px solid var(--panel-border);
        border-radius: 10px;
        padding: 1.2rem 1.5rem;
        cursor: pointer;
        margin-bottom: 1rem;
    }
    .mode-card-active {
        border-color: var(--ink);
    }
    .mode-title {
        font-size: 1rem;
        font-weight: 600;
        color: var(--ink);
        margin-bottom: 0.2rem;
    }
    .mode-desc {
        font-size: 0.82rem;
        color: var(--ink-faint);
    }
    .badge-row {
        display: flex;
        gap: 8px;
        margin-bottom: 2rem;
        flex-wrap: wrap;
    }
    .badge {
        background-color: var(--panel);
        border: 1px solid var(--panel-border);
        border-radius: 20px;
        padding: 3px 12px;
        font-size: 0.75rem;
        color: var(--ink-faint);
    }
    .footer-text {
        color: var(--hairline);
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
        color: var(--ink-faint);
        padding-top: 1.8rem;
    }
    .history-item {
        background-color: var(--panel);
        border: 1px solid var(--panel-border);
        border-radius: 8px;
        padding: 0.6rem 0.8rem;
        margin-bottom: 0.5rem;
    }
    .history-company {
        color: var(--ink);
        font-size: 0.88rem;
        font-weight: 600;
    }
    .history-time {
        color: var(--ink-faint);
        font-size: 0.72rem;
        margin-top: 0.1rem;
    }

    /* ── Sidebar ── */
    section[data-testid="stSidebar"] {
        background-color: var(--panel-alt) !important;
        border-right: 1px solid var(--hairline) !important;
    }
    section[data-testid="stSidebar"] .stButton > button {
        background-color: var(--panel) !important;
        color: var(--ink-dim) !important;
        border: 1px solid var(--panel-border) !important;
        font-weight: 500 !important;
        font-size: 0.8rem !important;
        padding: 0.4rem 0.8rem !important;
    }

    /* ── Mode toggle pill ── */
    .theme-toggle-row {
        display: flex;
        justify-content: flex-end;
        margin-bottom: 1.5rem;
    }
    .theme-label {
        font-size: 0.75rem;
        color: var(--ink-faint);
        letter-spacing: 0.6px;
        text-transform: uppercase;
        padding-top: 0.55rem;
        margin-right: 0.5rem;
    }
"""


def inject_theme(mode: str) -> None:
    """
    Call once at the top of app.py after set_page_config.

    mode: "Brief" (dark) | "Console" (light)
    """
    palette = BRIEF_CSS if mode == "Brief" else CONSOLE_CSS
    st_css = f"<style>{palette}{SHARED_CSS}</style>"

    import streamlit as st
    st.markdown(st_css, unsafe_allow_html=True)