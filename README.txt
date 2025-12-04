================================
1.) Make sure you have Ollama(pull a model) & python / pip installed 
2.) Run 'AI Counsel.bat' as an administrator
3.) Open your web browser and go to localhost:5000
4.) Sometimes server(app.py) gets stuck from too many HTTP requests. 
	(press any key in the terminal to push it along although.. 
	When it gets stuck the bots can start to halucinate & lose context..) 

Limerita Deep Research v2.1 (WORK IN PROGRESS)
Local Multi-Agent Research System with Democratic Voting
A fully offline research assistant powered by Ollama. Combines web search, multi-agent analysis, peer voting, and final synthesis — all running locally with zero telemetry.
Core Features

Two research modes:
Single Pass: Direct query → web search → LLM answer
Counsel Mode: 3–7 specialized AI agents independently analyze the same research data → vote on the best contribution → final synthesis by a dedicated synthesizer

Real-time voting visualization with per-agent vote bars
Automatic source collection and deduplicated source sidebar
Local chat & memory persistence (chats.json, memory.json)
Works with any Ollama model (Llama 3.2, Phi-3, Gemma 2, Qwen2.5, Mistral, etc.)

Search Pipeline
Primary search attempts (in order):

DuckDuckGo Instant Answer API
DuckDuckGo HTML fallback (light scraping)
Curated high-quality sources (Wikipedia, Google Scholar, Britannica, Reddit, Stack Overflow, GitHub — context-aware)

All requests include randomized User-Agent, 3–8 second delays, and respect robots.txt when possible.
Quick Start
Bashgit clone https://github.com/yourusername/limerita-deep-research.git
cd limerita-deep-research
Windows: Double-click AI Counsel.bat
macOS/Linux: python3 start.py
First run will prompt to install missing packages (requests, flask, flask-cors, beautifulsoup4) — answer y.
Then open http://localhost:5000
Tech Stack

Backend: Flask + Flask-CORS
Frontend: React 18 + Tailwind + Babel standalone
AI: Ollama (localhost:11434)
Search: DuckDuckGo + curated fallbacks
Storage: Local JSON files

Project Structure
textAI Counsel.bat      → Windows launcher
start.py            → Dependency checker + Ollama starter + starts application
app.py              → Core Flask server + counsel logic
index.html          → Full frontend (React + retro CRT UI)
chats.json          → Saved conversations 
memory.json         → Research session memory 
LICENSE             → MIT
Work in Progress / Upcoming

Full memory integration (context from past sessions automatically injected)
Manual source selection / pinning
Pre-search query refinement (LLM generates targeted search terms before crawling)
Real peer evaluation voting (agents critique each other instead of random votes)

Ethical & Legal Use
This tool performs web searching and limited content extraction for personal, non-commercial research only.

Respects robots.txt when available
Includes deliberate delays to avoid overloading servers
You are responsible for complying with each website’s Terms of Service
Do not use for bulk scraping, spam, or any illegal activity

License












									-Limerita 2025
================================
