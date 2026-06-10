import streamlit as st
from crew.crew import run_crew

st.set_page_config(
    page_title="StartupScope",
    page_icon="🔍",
    layout="centered"
)

st.title("StartupScope")
st.caption("Multi-agent startup intelligence powered by CrewAI + Groq")
st.markdown("---")

company_name = st.text_input(
    "Company name",
    placeholder="e.g. Zepto, Razorpay, Notion, OpenAI..."
)

if st.button("Generate Report", type="primary", disabled=not company_name):
    with st.spinner(f"Researching {company_name}... This takes 60-90 seconds."):
        try:
            result, saved_path = run_crew(company_name)
            st.success(f"Report complete! Saved to {saved_path}")
            st.markdown("---")
            st.markdown(result)
            st.download_button(
                label="Download report (.md)",
                data=result,
                file_name=f"{company_name.lower().replace(' ', '_')}_report.md",
                mime="text/markdown"
            )
        except Exception as e:
            st.error(f"Something went wrong: {str(e)}")
            st.info("Check your API keys in .env and try again.")

st.markdown("---")
st.caption("Built with CrewAI · LangChain · Groq · Streamlit")
