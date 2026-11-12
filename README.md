# KaleemGPT

An agentic AI chat assistant built with **FastAPI + LangGraph**. It streams answers token by token and can:

- **Search the web** for current information (Tavily)
- **Chat with your documents**: upload PDF, DOCX, TXT, MD, CSV or code files (Chroma + Gemini embeddings)
- **Remember things about you** across conversations (long-term memory)
- **Do exact math** with a safe calculator tool
- Switch between **models** (GPT-OSS 20B/120B on Groq; Gemini 3.8 Flash, Gemini 3 Flash and Gemini 3.5 Flash-Lite on Google) and **agent modes** (General, Coding, Research, Document, Data)

The UI includes chat history, search, rename/delete, regenerate, stop generation, markdown with syntax highlighting, voice input and read-aloud, dark/light themes, and a mobile layout.

## Quick start

```bash
git clone https://github.com/KaleemZdk/KaleemGpt.git
cd KaleemGpt
python -m venv .venv && source .venv/bin/activate   # or: conda create -n kaleemgpt python=3.12
pip install -r requirements.txt
```

Create a `.env` file in the project root:

```env
GROQ_API_KEY=...        # GPT-OSS models (https://console.groq.com)
GEMINI_API_KEY=...      # Gemini models + document upload/search (https://aistudio.google.com)
TAVILY_API_KEY=...      # web search (https://tavily.com)
```

You need at least one of `GROQ_API_KEY` / `GEMINI_API_KEY`. Each missing key only disables the features that depend on it. The app still starts.

Run it:

```bash
python app.py            # dev mode with auto-reload
# or
uvicorn app:app --host 0.0.0.0 --port 8080
```

Open http://localhost:8080.

## Configuration

| Variable | Default | Purpose |
|---|---|---|
| `DEFAULT_MODEL` | `openai/gpt-oss-20b` | Default model (any id from the model menu; `GROQ_MODEL` still works) |
| `DATA_DIR` | `./data` | SQLite DBs + Chroma vector index |
| `UPLOAD_DIR` | `./uploads` | Uploaded files (one folder per conversation) |
| `MAX_UPLOAD_MB` | `20` | Max upload size |
| `MAX_HISTORY_MESSAGES` | `40` | Past messages sent to the model each turn |

## Project layout

```
app.py          FastAPI routes (chat SSE stream, uploads, conversations, memories)
agent.py        LangGraph agent, model registry, agent modes, history trimming
tool.py         Tools: web search, calculator, document search, memory
rag.py          Document parsing, chunking, Chroma vector store
database.py     SQLAlchemy models: conversations, messages, memories
config.py       Paths and environment settings
templates/      HTML shell
static/         CSS + JS (served with cache-busting)
tests/          pytest suite (runs with a fake LLM, no API keys needed)
```

## Tests

```bash
pip install pytest httpx
pytest -q
```

## Docker

```bash
docker build -t kaleemgpt .
docker run -p 8080:8080 --env-file .env \
  -v kaleemgpt_data:/app/data -v kaleemgpt_uploads:/app/uploads kaleemgpt
```

Pushing to `main` runs CI (lint, tests), builds the image and deploys it to EC2 (`.github/workflows/cicd.yaml`).
