# StartupScope — AI-Powered Startup Intelligence Tool
> A multi-agent research tool that automatically researches any startup or company and generates a structured intelligence report — covering funding, business model, competitors, strengths, risks, and recent news.

## 🌐 Live Demo
👉 https://startupscope-ephq.onrender.com

> ⚡ Hosted on Render free tier — may take 15-20 seconds to wake up on first visit.

---

## 📸 What it does
- Type any company name (e.g. Razorpay, Zepto, Notion)
- 3 AI agents research, analyze, and write a full report
- Get funding history, business model, competitors, strengths, risks
- Download the report as a markdown file

---

## Features
- **Multi-Agent System** — 3 specialized agents work sequentially (Researcher → Analyst → Writer)
- **Live Web Search** — Agents search the internet in real-time via Serper API
- **Intelligence Report** — Structured markdown report with 9 sections
- **Download Report** — Save the report as a `.md` file
- **Clean Dark UI** — Professional dark-themed interface

---

## Tech Stack
| Layer | Tech |
|-------|------|
| Agent Framework | CrewAI |
| LLM | Groq API (LLaMA 3.3 70B) |
| Web Search | Serper Dev API |
| Frontend | Streamlit |
| Deployment | Render |

---

## Project Structure
```
startupscope/
├── app.py                  # Streamlit UI
├── main.py                 # Terminal runner
├── requirements.txt        # Python dependencies
├── render.yaml             # Render deployment config
├── .env                    # API keys (not committed)
├── .gitignore
├── crew/
│   ├── agents.py           # 3 agent definitions
│   ├── tasks.py            # 3 task definitions
│   └── crew.py             # Crew assembly and runner
├── tools/
│   └── search_tool.py      # Serper web search tool
└── outputs/                # Generated reports saved here
```

---

## Setup & Installation

### 1. Clone the repository
```bash
git clone https://github.com/ayush-s-tomar/startupscope.git
cd startupscope
```

### 2. Install dependencies
```bash
pip install -r requirements.txt
```

### 3. Set up your API keys
Get your free Groq key at [console.groq.com](https://console.groq.com)
Get your free Serper key at [serper.dev](https://serper.dev)

Create a `.env` file in the root directory:
```
GROQ_API_KEY=your_groq_key_here
SERPER_API_KEY=your_serper_key_here
```

### 4. Run the app
```bash
streamlit run app.py
```
Open your browser and go to: **http://localhost:8501**

---

## How to Use
1. Open the app in your browser
2. Type any company name in the input field
3. Click **Generate Intelligence Report**
4. Wait 60–90 seconds while the 3 agents work
5. Read the report and download it as `.md`

---

## How the Agents Work
```
User Input (Company Name)
        ↓
[Agent 1: Researcher]
Searches the web, collects raw data
        ↓
[Agent 2: Analyst]
Extracts insights, identifies strengths & risks
        ↓
[Agent 3: Writer]
Formats everything into a clean report
        ↓
Intelligence Report
```

---

## Deployment (Free on Render)
1. Push this repo to GitHub
2. Go to [render.com](https://render.com) → New → Web Service
3. Connect your GitHub repo
4. Set **Build Command**: `pip install -r requirements.txt`
5. Set **Start Command**: `streamlit run app.py --server.port $PORT --server.address 0.0.0.0`
6. Add environment variables: `GROQ_API_KEY` and `SERPER_API_KEY`
7. Deploy!

---

## What I Learned
- Building multi-agent AI systems with CrewAI
- Integrating LLM APIs (Groq — LLaMA 3.3 70B)
- Real-time web search integration with Serper
- Sequential agent orchestration and task chaining
- Deploying Streamlit apps on Render

---

## License
MIT License — feel free to use and modify.

---

Built by [Ayush Singh Tomar](https://github.com/ayush-s-tomar)
