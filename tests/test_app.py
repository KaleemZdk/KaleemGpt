import os
import subprocess
import sys
import uuid
from pathlib import Path

from conftest import parse_sse
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage

ROOT = Path(__file__).resolve().parents[1]


def tid() -> str:
    return uuid.uuid4().hex[:16]


def chat(client, thread_id, message="", **extra):
    res = client.post("/chat/stream", json={"message": message, "thread_id": thread_id, **extra})
    assert res.status_code == 200, res.text
    return parse_sse(res.text)


def tokens(events):
    return "".join(e.get("token", "") for e in events)


# ----------------------------------------------------------------------------
# Pages & config
# ----------------------------------------------------------------------------

def test_home_page_and_static_assets(client):
    res = client.get("/")
    assert res.status_code == 200
    assert "/static/js/app.js?v=" in res.text

    js = client.get("/static/js/app.js?v=1")
    assert js.status_code == 200
    assert "immutable" in js.headers["cache-control"]


def test_config_lists_models_and_agents(client):
    cfg = client.get("/config").json()
    ids = [m["id"] for m in cfg["models"]]
    assert "openai/gpt-oss-20b" in ids
    assert {a["key"] for a in cfg["agents"]} == {"general", "coding", "research", "document", "data"}
    assert cfg["features"]["web_search"] is False  # no TAVILY key in tests
    assert ".pdf" in cfg["upload"]["extensions"]


def test_app_imports_without_any_api_keys():
    """Missing TAVILY/GEMINI keys used to crash the app at import time."""
    env = {k: v for k, v in os.environ.items() if not k.endswith("_API_KEY")}
    env["DATA_DIR"] = os.environ["DATA_DIR"]
    out = subprocess.run(
        [sys.executable, "-c", "import app; from fastapi.testclient import TestClient; "
         "c = TestClient(app.app); print(c.get('/config').json()['models'])"],
        cwd=ROOT, env=env, capture_output=True, text=True, timeout=120,
    )
    assert out.returncode == 0, out.stderr
    assert out.stdout.strip().endswith("[]")


# ----------------------------------------------------------------------------
# Chat
# ----------------------------------------------------------------------------

def test_chat_streams_tokens_and_persists(client, fake_llm):
    fake_llm.responses = ["Hello there, Kaleem!"]
    t = tid()
    events = chat(client, t, "Hi, my name is Kaleem and I like building agents")

    assert tokens(events) == "Hello there, Kaleem!"
    done = [e for e in events if e.get("done")]
    assert done and done[0]["message_id"]

    convs = client.get("/conversations").json()["conversations"]
    conv = next(c for c in convs if c["thread_id"] == t)
    assert conv["title"].startswith("Hi, my name is Kaleem")
    assert conv["updated_at"].endswith("Z")

    history = client.get(f"/history/{t}").json()["messages"]
    assert [m["role"] for m in history] == ["user", "assistant"]
    assert history[1]["content"] == "Hello there, Kaleem!"


def test_follow_up_turn_sees_previous_messages(client, fake_llm):
    fake_llm.responses = ["First answer", "Second answer"]
    t = tid()
    chat(client, t, "first question")
    chat(client, t, "second question")
    sent = fake_llm.calls[-1]
    texts = [m.content for m in sent]
    assert "first question" in texts and "First answer" in texts and "second question" in texts


def test_tool_call_emits_status_and_runs_tool(client, fake_llm):
    fake_llm.responses = [
        AIMessage(content="", tool_calls=[{"name": "remember_this", "args": {"memory": "User prefers tea"}, "id": "c1"}]),
        "Got it, I'll remember that.",
    ]
    t = tid()
    events = chat(client, t, "remember that I prefer tea")

    assert {"status": "Saving to memory"} in events
    assert tokens(events) == "Got it, I'll remember that."
    memories = client.get("/memories").json()["memories"]
    assert any(m["memory"] == "User prefers tea" for m in memories)

    # Memory is long-term: visible from a different conversation too.
    import database
    assert "User prefers tea" in database.search_memory("what drink do I like")


def test_agent_mode_changes_system_prompt(client, fake_llm):
    fake_llm.responses = ["ok"]
    chat(client, tid(), "fix my code", agent="coding")
    system = fake_llm.calls[-1][0].content
    assert "senior software engineer" in system
    assert "KaleemGPT" in system


def test_regenerate_replaces_last_answer(client, fake_llm):
    fake_llm.responses = ["Answer one", "Answer two"]
    t = tid()
    chat(client, t, "tell me something")
    events = chat(client, t, regenerate=True)
    assert tokens(events) == "Answer two"

    history = client.get(f"/history/{t}").json()["messages"]
    assert [(m["role"], m["content"]) for m in history] == [("user", "tell me something"), ("assistant", "Answer two")]

    # The model must not see the discarded answer or a duplicated question.
    sent = [m.content for m in fake_llm.calls[-1][1:]]
    assert sent == ["tell me something"]


def test_empty_message_rejected(client):
    res = client.post("/chat/stream", json={"message": "   ", "thread_id": tid()})
    assert res.status_code == 400


def test_invalid_thread_id_rejected(client):
    assert client.post("/chat/stream", json={"message": "hi", "thread_id": "../etc"}).status_code == 400
    assert client.get("/history/bad id").status_code == 400


def test_provider_error_is_reported_in_stream(client, fake_llm):
    fake_llm.responses = []  # pop() from empty list -> exception inside the graph
    events = chat(client, tid(), "hello")
    assert any("error" in e for e in events)
    assert events[-1].get("done")


# ----------------------------------------------------------------------------
# Conversations management
# ----------------------------------------------------------------------------

def test_rename_and_delete_conversation(client, fake_llm):
    fake_llm.responses = ["hey"]
    t = tid()
    chat(client, t, "hello")

    res = client.patch(f"/conversations/{t}", json={"title": "Renamed chat"})
    assert res.status_code == 200 and res.json()["title"] == "Renamed chat"

    assert client.delete(f"/conversations/{t}").json()["success"]
    assert all(c["thread_id"] != t for c in client.get("/conversations").json()["conversations"])
    assert client.get(f"/history/{t}").json()["messages"] == []
    assert client.patch(f"/conversations/{t}", json={"title": "x"}).status_code == 404


def test_delete_memory(client):
    import database

    database.save_memory("t", "Temporary fact")
    mid = next(m["id"] for m in client.get("/memories").json()["memories"] if m["memory"] == "Temporary fact")
    assert client.delete(f"/memories/{mid}").status_code == 200
    assert client.delete(f"/memories/{mid}").status_code == 404


# ----------------------------------------------------------------------------
# Uploads & RAG
# ----------------------------------------------------------------------------

def test_upload_rejects_unsupported_type(client):
    res = client.post("/upload", data={"thread_id": tid()}, files={"file": ("virus.exe", b"MZ", "application/octet-stream")})
    assert res.status_code == 400
    assert res.json()["success"] is False


def test_upload_sanitizes_path_and_scopes_documents_to_thread(client, fake_vectorstore):
    import tool
    from config import UPLOAD_DIR

    t1, t2 = tid(), tid()
    res = client.post(
        "/upload",
        data={"thread_id": t1},
        files={"file": ("../../evil notes.txt", b"The secret project codename is BLUEBIRD.", "text/plain")},
    )
    assert res.status_code == 200, res.text
    assert res.json()["chunks"] == 1

    saved = list((UPLOAD_DIR / t1).iterdir())
    assert len(saved) == 1 and saved[0].name.endswith("evil_notes.txt")

    found = tool.search_uploaded_documents.invoke({"query": "codename"}, config={"configurable": {"thread_id": t1}})
    assert "BLUEBIRD" in found
    other = tool.search_uploaded_documents.invoke({"query": "codename"}, config={"configurable": {"thread_id": t2}})
    assert "BLUEBIRD" not in other

    client.delete(f"/conversations/{t1}")
    assert not (UPLOAD_DIR / t1).exists()
    assert fake_vectorstore.get(where={"thread_id": t1})["ids"] == []


# ----------------------------------------------------------------------------
# Units
# ----------------------------------------------------------------------------

def test_calculator():
    from tool import calculator

    assert calculator.invoke({"expression": "342 × 4,234 ÷ 3"}) == "482676"
    assert calculator.invoke({"expression": "sqrt(144) + 2**10"}) == "1036"
    assert calculator.invoke({"expression": "round(3.14159, 2)"}) == "3.14"
    assert "unsafe" in calculator.invoke({"expression": "__import__('os').system('ls')"})
    assert "too large" in calculator.invoke({"expression": "9**99999"})


def test_trim_history_starts_at_user_message():
    from agent import trim_history

    msgs = []
    for i in range(30):
        msgs += [HumanMessage(content=f"q{i}"), AIMessage(content=f"a{i}")]
    out = trim_history(msgs, limit=7)
    assert isinstance(out[0], HumanMessage)
    assert out[-1].content == "a29" and len(out) <= 7


def test_dangling_tool_calls_are_dropped():
    from agent import drop_dangling_tool_calls

    msgs = [
        HumanMessage(content="search"),
        AIMessage(content="", tool_calls=[{"name": "web_search", "args": {"query": "x"}, "id": "lost"}]),
        HumanMessage(content="hello again"),
        AIMessage(content="", tool_calls=[{"name": "calculator", "args": {"expression": "1+1"}, "id": "ok"}]),
        ToolMessage(content="2", tool_call_id="ok"),
        AIMessage(content="It's 2"),
    ]
    out = drop_dangling_tool_calls(msgs)
    assert len(out) == 5
    assert all(getattr(m, "tool_calls", None) is None or m.tool_calls[0]["id"] == "ok" for m in out if isinstance(m, AIMessage) and m.tool_calls)
