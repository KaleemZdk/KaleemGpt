import os
import sqlite3
import threading
from datetime import UTC, datetime

from langchain_core.messages import (
    AIMessage,
    HumanMessage,
    RemoveMessage,
    SystemMessage,
    ToolMessage,
)
from langchain_core.runnables import RunnableConfig
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.graph import END, START, MessagesState, StateGraph
from langgraph.prebuilt import ToolNode

from config import CHECKPOINT_DB, MAX_HISTORY_MESSAGES, has_env
from tool import tools

# ----------------------------------------------------------------------------
# Models
# ----------------------------------------------------------------------------

# Verified against the live Groq / Gemini model lists (Nov 2026) with a tool-calling
# smoke test. Every model here must support tool calling and streaming.
MODELS = {
    "openai/gpt-oss-20b": {
        "name": "GPT-OSS 20B", "description": "Fast everyday model", "provider": "groq",
    },
    "openai/gpt-oss-120b": {
        "name": "GPT-OSS 120B", "description": "Smarter, a bit slower", "provider": "groq",
    },
    "gemini-3-flash-preview": {
        "name": "Gemini 3 Flash", "description": "Strong reasoning, preview release", "provider": "google",
    },
    "gemini-3.5-flash-lite": {
        "name": "Gemini 3.5 Flash-Lite", "description": "Lightest, quickest Gemini", "provider": "google",
    },
    # Newest Gemini, but the free tier allows only ~20 requests/day and it is often overloaded.
    "gemini-3.8-flash": {
        "name": "Gemini 3.8 Flash", "description": "Newest Gemini, low free-tier daily limit", "provider": "google",
    },
}

PROVIDER_KEYS = {"groq": ("GROQ_API_KEY",), "google": ("GEMINI_API_KEY", "GOOGLE_API_KEY")}


def provider_ready(provider: str) -> bool:
    return any(has_env(k) for k in PROVIDER_KEYS.get(provider, ()))


def available_models() -> list[dict]:
    return [
        {"id": mid, **{k: v for k, v in meta.items() if k != "provider"}}
        for mid, meta in MODELS.items()
        if provider_ready(meta["provider"])
    ]


def default_model() -> str:
    # DEFAULT_MODEL may name any model; GROQ_MODEL is the older name for the same setting.
    preferred = (os.getenv("DEFAULT_MODEL") or os.getenv("GROQ_MODEL") or "").strip() or "openai/gpt-oss-20b"
    ids = [m["id"] for m in available_models()]
    if preferred in ids:
        return preferred
    return ids[0] if ids else preferred


def normalize_model_name(model_name: str | None) -> str:
    model_name = (model_name or "").strip()
    if model_name in MODELS and provider_ready(MODELS[model_name]["provider"]):
        return model_name
    return default_model()


def make_llm(model_name: str):
    provider = MODELS.get(model_name, {}).get("provider", "groq")
    if provider == "google":
        from langchain_google_genai import ChatGoogleGenerativeAI

        return ChatGoogleGenerativeAI(
            model=model_name,
            google_api_key=os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY"),
            # Gemini 3+ is tuned for the default temperature (1.0); lowering it can cause loops.
            # The default 6 retries made an overloaded model hang the chat for minutes.
            max_retries=2,
            timeout=90,
        )

    from langchain_groq import ChatGroq

    return ChatGroq(model=model_name, groq_api_key=os.getenv("GROQ_API_KEY"), streaming=True, temperature=0.6,
                    max_retries=2, timeout=90)


# ----------------------------------------------------------------------------
# Agent modes (the "agent" picker in the UI)
# ----------------------------------------------------------------------------

AGENT_MODES = {
    "general": {
        "name": "General Assistant", "description": "Chat, answer questions, help with tasks", "icon": "sparkles",
        "prompt": "",
    },
    "coding": {
        "name": "Coding Agent", "description": "Write, debug, and explain code", "icon": "code",
        "prompt": (
            "You are acting as a senior software engineer. Prefer complete, runnable code in fenced "
            "code blocks with the language tag. Explain bugs by root cause, then show the fix. "
            "Keep explanations tight."
        ),
    },
    "research": {
        "name": "Research Agent", "description": "Search the web and analyze information", "icon": "search",
        "prompt": (
            "You are acting as a research analyst. Use web_search for anything that could have changed "
            "recently. Compare sources, note disagreements, and cite URLs inline as markdown links."
        ),
    },
    "document": {
        "name": "Document Assistant", "description": "Analyze and summarize your documents", "icon": "file",
        "prompt": (
            "You are acting as a document analyst. Ground every answer in search_uploaded_documents, "
            "quote short passages when useful and name the source file. Say clearly when the documents "
            "don't contain the answer."
        ),
    },
    "data": {
        "name": "Data Analyst", "description": "Analyze data and create insights", "icon": "chart",
        "prompt": (
            "You are acting as a data analyst. Use the calculator for every arithmetic step, present "
            "results in markdown tables when there is more than one number, and end with the key insight."
        ),
    },
}


def normalize_agent_mode(mode: str | None) -> str:
    return mode if mode in AGENT_MODES else "general"


SYSTEM_PROMPT = """You are KaleemGPT, a helpful agentic AI assistant.

Today's date is {today}.

You can:
1. Answer questions and help with tasks directly.
2. Search the documents uploaded in this conversation (search_uploaded_documents).
3. Search the web for current information (web_search).
4. Save and recall facts about the user across conversations (remember_this / recall_memory).
5. Do exact math with the calculator.

Rules:
- For latest news, current events, prices, or anything time-sensitive, use web_search and mention the answer is based on web results, citing sources as markdown links.
- If the user mentions an attached/uploaded file or document, use search_uploaded_documents.
- If the user asks you to remember something, use remember_this. If they ask what you know about them, use recall_memory.
- Use the calculator for arithmetic instead of doing it in your head.
- Be clear, helpful, and concise. Use markdown (headings, lists, tables, fenced code) when it helps readability.

Formatting rules:
- Never output bracket citation markers like 【1】 or 【source†L1-L3】. Cite only as markdown links, or name the source file.
- Never use LaTeX or math markup (no \\[ \\], \\( \\), \\frac, \\times).
- Write math in plain text, like: 342 × 4,234 ÷ 3 = 482,676.
- For calculations, show short numbered steps, then the final answer in bold on its own line.
"""


def build_system_prompt(mode: str) -> str:
    prompt = SYSTEM_PROMPT.format(today=datetime.now(UTC).strftime("%A, %d %B %Y"))
    extra = AGENT_MODES[normalize_agent_mode(mode)]["prompt"]
    return prompt + (f"\nCurrent mode: {extra}\n" if extra else "")


# ----------------------------------------------------------------------------
# History hygiene
# ----------------------------------------------------------------------------

def drop_dangling_tool_calls(messages: list) -> list:
    """Remove AI tool calls that never got a result (e.g. the user pressed Stop mid-tool).

    Providers reject a history where a tool call isn't followed by its tool result,
    which would otherwise break the conversation permanently.
    """
    answered = {m.tool_call_id for m in messages if isinstance(m, ToolMessage)}
    bad: set[str] = set()
    out = []
    for m in messages:
        if isinstance(m, AIMessage) and m.tool_calls:
            ids = {tc.get("id") for tc in m.tool_calls}
            if not ids <= answered:
                bad |= ids
                continue
        if isinstance(m, ToolMessage) and m.tool_call_id in bad:
            continue
        out.append(m)
    return out


def trim_history(messages: list, limit: int = MAX_HISTORY_MESSAGES) -> list:
    """Send only recent turns to the model, always starting at a user message."""
    if len(messages) <= limit:
        return messages
    recent = messages[-limit:]
    for i, m in enumerate(recent):
        if isinstance(m, HumanMessage):
            return recent[i:]
    # A single very long tool loop: keep everything since the last user message.
    for i in range(len(messages) - 1, -1, -1):
        if isinstance(messages[i], HumanMessage):
            return messages[i:]
    return recent


# ----------------------------------------------------------------------------
# Graph
# ----------------------------------------------------------------------------

_checkpointer = None
_cp_lock = threading.Lock()


def get_checkpointer() -> SqliteSaver:
    """One shared checkpointer/connection for all models (it has its own lock)."""
    global _checkpointer
    if _checkpointer is None:
        with _cp_lock:
            if _checkpointer is None:
                conn = sqlite3.connect(str(CHECKPOINT_DB), check_same_thread=False)
                conn.execute("PRAGMA journal_mode=WAL")
                _checkpointer = SqliteSaver(conn)
    return _checkpointer


def route_after_chatbot(state: MessagesState):
    messages = state.get("messages") or []
    if messages and isinstance(messages[-1], AIMessage) and messages[-1].tool_calls:
        return "tools"
    return END


def build_agent(model_name: str, llm=None):
    """Build one LangGraph agent for a model. `llm` can be injected for tests."""
    llm_with_tools = (llm or make_llm(model_name)).bind_tools(tools)

    def chatbot_node(state: MessagesState, config: RunnableConfig):
        mode = ((config or {}).get("configurable") or {}).get("agent_mode", "general")
        history = trim_history(drop_dangling_tool_calls(state["messages"]))
        response = llm_with_tools.invoke([SystemMessage(content=build_system_prompt(mode))] + history, config)
        return {"messages": [response]}

    workflow = StateGraph(MessagesState)
    workflow.add_node("chatbot", chatbot_node)
    workflow.add_node("tools", ToolNode(tools))
    workflow.add_edge(START, "chatbot")
    workflow.add_conditional_edges("chatbot", route_after_chatbot, ["tools", END])
    workflow.add_edge("tools", "chatbot")

    return workflow.compile(checkpointer=get_checkpointer())


_AGENT_CACHE: dict = {}
_agent_lock = threading.Lock()


def get_agent(model_name: str | None = None):
    """Return the cached agent for a model, building it once."""
    selected = normalize_model_name(model_name)
    if selected not in _AGENT_CACHE:
        with _agent_lock:
            if selected not in _AGENT_CACHE:
                _AGENT_CACHE[selected] = build_agent(selected)
    return _AGENT_CACHE[selected]


def rewind_last_turn(agent, config: dict) -> None:
    """Drop the last user message and everything after it from the graph state (for Regenerate)."""
    snapshot = agent.get_state(config)
    messages = (snapshot.values or {}).get("messages", []) if snapshot else []
    last_human = next((i for i in range(len(messages) - 1, -1, -1) if isinstance(messages[i], HumanMessage)), None)
    if last_human is None:
        return
    removals = [RemoveMessage(id=m.id) for m in messages[last_human:] if m.id]
    if removals:
        agent.update_state(config, {"messages": removals}, as_node="chatbot")


def delete_thread_state(thread_id: str) -> None:
    try:
        get_checkpointer().delete_thread(thread_id)
    except Exception:
        pass
