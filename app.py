import hashlib
import json
import logging
import re
import shutil
import uuid
from pathlib import Path

import uvicorn
from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.concurrency import run_in_threadpool
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from langchain_core.messages import AIMessage, AIMessageChunk, HumanMessage, ToolMessage
from pydantic import BaseModel, Field

from agent import (
    AGENT_MODES,
    available_models,
    default_model,
    delete_thread_state,
    get_agent,
    normalize_agent_mode,
    normalize_model_name,
    rewind_last_turn,
)
from config import BASE_DIR, MAX_UPLOAD_MB, UPLOAD_DIR
from database import (
    all_thread_ids,
    create_or_update_conversation,
    delete_conversation,
    delete_memory,
    delete_messages_after,
    get_chat_history,
    get_last_user_message,
    init_db,
    list_conversations,
    list_memories,
    rename_conversation,
    save_chat_message,
)
from rag import (
    SUPPORTED_SUFFIXES,
    add_document_to_rag,
    delete_thread_documents,
    rag_available,
)
from tool import TOOL_STATUS, web_search_available

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger("kaleemgpt")

app = FastAPI(title="KaleemGPT")
# Compresses HTML/CSS/JS/JSON. Starlette skips text/event-stream, so streaming is unaffected.
app.add_middleware(GZipMiddleware, minimum_size=1024)

STATIC_DIR = BASE_DIR / "static"


class VersionedStaticFiles(StaticFiles):
    """Assets are requested as /static/x.js?v=<hash>, so they can be cached for a year."""

    async def get_response(self, path, scope):
        response = await super().get_response(path, scope)
        if response.status_code == 200 and b"v=" in scope.get("query_string", b""):
            response.headers["Cache-Control"] = "public, max-age=31536000, immutable"
        return response


app.mount("/static", VersionedStaticFiles(directory=STATIC_DIR), name="static")
templates = Jinja2Templates(directory=BASE_DIR / "templates")

init_db()


def _asset_version() -> str:
    """Cache-busting hash of the static files, computed once at startup."""
    h = hashlib.md5()
    for p in sorted(STATIC_DIR.rglob("*")):
        if p.is_file():
            h.update(p.read_bytes())
    return h.hexdigest()[:10]


ASSET_VERSION = _asset_version()

THREAD_ID_RE = re.compile(r"^[A-Za-z0-9_-]{1,64}$")


def check_thread_id(thread_id: str) -> str:
    if not THREAD_ID_RE.match(thread_id or ""):
        raise HTTPException(status_code=400, detail="Invalid thread id.")
    return thread_id


# ----------------------------------------------------------------------------
# Pages & config
# ----------------------------------------------------------------------------

@app.get("/")
def home(request: Request):
    return templates.TemplateResponse(request=request, name="index.html", context={"v": ASSET_VERSION})


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/config")
def get_config():
    return {
        "models": available_models(),
        "default_model": default_model(),
        "agents": [
            {"key": k, "name": v["name"], "description": v["description"], "icon": v["icon"]}
            for k, v in AGENT_MODES.items()
        ],
        "features": {
            "web_search": web_search_available(),
            "documents": rag_available(),
        },
        "upload": {"extensions": sorted(SUPPORTED_SUFFIXES), "max_mb": MAX_UPLOAD_MB},
    }


# ----------------------------------------------------------------------------
# Conversations
# ----------------------------------------------------------------------------

class RenameBody(BaseModel):
    title: str = Field(min_length=1, max_length=120)


@app.get("/conversations")
def conversations():
    return {"conversations": list_conversations()}


@app.patch("/conversations/{thread_id}")
def rename(thread_id: str, body: RenameBody):
    conv = rename_conversation(check_thread_id(thread_id), body.title)
    if conv is None:
        raise HTTPException(status_code=404, detail="Conversation not found.")
    return conv


def _purge_thread(thread_id: str) -> None:
    delete_conversation(thread_id)
    delete_thread_state(thread_id)
    delete_thread_documents(thread_id)
    shutil.rmtree(UPLOAD_DIR / thread_id, ignore_errors=True)


@app.delete("/conversations/{thread_id}")
def remove_conversation(thread_id: str):
    _purge_thread(check_thread_id(thread_id))
    return {"success": True}


@app.delete("/conversations")
def remove_all_conversations():
    for tid in all_thread_ids():
        _purge_thread(tid)
    return {"success": True}


@app.get("/history/{thread_id}")
def history(thread_id: str):
    return {"messages": get_chat_history(check_thread_id(thread_id))}


# ----------------------------------------------------------------------------
# Memories
# ----------------------------------------------------------------------------

@app.get("/memories")
def memories():
    return {"memories": list_memories()}


@app.delete("/memories/{memory_id}")
def remove_memory(memory_id: int):
    if not delete_memory(memory_id):
        raise HTTPException(status_code=404, detail="Memory not found.")
    return {"success": True}


# ----------------------------------------------------------------------------
# Uploads
# ----------------------------------------------------------------------------

def _safe_filename(name: str) -> str:
    # Path(...).name strips any directory part ("../../etc/passwd" -> "passwd").
    base = Path(name or "upload").name
    base = re.sub(r"[^\w.\- ]", "_", base).strip().replace(" ", "_")
    return base[:120] or "upload"


@app.post("/upload")
async def upload_document(file: UploadFile = File(...), thread_id: str = Form(...)):
    check_thread_id(thread_id)
    original = file.filename or "upload"
    suffix = Path(original).suffix.lower()

    if suffix not in SUPPORTED_SUFFIXES:
        allowed = ", ".join(s.lstrip(".").upper() for s in sorted(SUPPORTED_SUFFIXES))
        return JSONResponse({"success": False, "message": f"Unsupported file type. Allowed: {allowed}."}, 400)

    if not rag_available():
        return JSONResponse(
            {"success": False, "message": "Document upload is disabled: GEMINI_API_KEY is not configured."}, 503
        )

    data = await file.read()
    if len(data) > MAX_UPLOAD_MB * 1024 * 1024:
        return JSONResponse({"success": False, "message": f"File is larger than {MAX_UPLOAD_MB} MB."}, 413)

    thread_dir = UPLOAD_DIR / thread_id
    thread_dir.mkdir(parents=True, exist_ok=True)
    path = thread_dir / f"{uuid.uuid4().hex[:8]}_{_safe_filename(original)}"

    try:
        await run_in_threadpool(path.write_bytes, data)
        await run_in_threadpool(create_or_update_conversation, thread_id)
        # Parsing + embedding is slow and blocking: keep it off the event loop.
        result = await run_in_threadpool(add_document_to_rag, path, thread_id, original)
    except ValueError as e:
        path.unlink(missing_ok=True)
        return JSONResponse({"success": False, "message": str(e)}, 422)
    except Exception as e:
        path.unlink(missing_ok=True)
        log.exception("Upload failed")
        return JSONResponse({"success": False, "message": f"Could not process file: {e}"}, 500)

    return {
        "success": True,
        "filename": result["filename"],
        "chunks": result["chunks"],
        "message": f"Indexed {result['filename']} ({result['chunks']} chunks).",
    }


# ----------------------------------------------------------------------------
# Chat (Server-Sent Events)
# ----------------------------------------------------------------------------

class ChatRequest(BaseModel):
    message: str = ""
    thread_id: str = "default"
    model: str | None = None
    agent: str | None = None
    attachments: list[str] = Field(default_factory=list, max_length=10)
    regenerate: bool = False


def sse_data(payload: dict) -> str:
    return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"


def should_stream_chunk(chunk, metadata) -> bool:
    """Only forward assistant text — never raw tool calls or tool output."""
    if "tool" in str((metadata or {}).get("langgraph_node", "")).lower():
        return False
    if isinstance(chunk, ToolMessage) or not isinstance(chunk, (AIMessage, AIMessageChunk)):
        return False
    if getattr(chunk, "tool_calls", None) or getattr(chunk, "invalid_tool_calls", None):
        return False
    if (getattr(chunk, "additional_kwargs", {}) or {}).get("tool_calls"):
        return False
    return True


def tool_names_in_chunk(chunk) -> list[str]:
    names = [tc.get("name") for tc in getattr(chunk, "tool_call_chunks", None) or []]
    names += [tc.get("name") for tc in getattr(chunk, "tool_calls", None) or []]
    return [n for n in names if n]


def extract_text_from_chunk(chunk) -> str:
    content = getattr(chunk, "content", "")
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for item in content:
            if isinstance(item, str):
                parts.append(item)
            elif isinstance(item, dict) and item.get("type", "text") == "text" and isinstance(item.get("text"), str):
                parts.append(item["text"])
        return "".join(parts)
    return ""


@app.post("/chat/stream")
def chat_stream(body: ChatRequest):
    thread_id = check_thread_id(body.thread_id)
    model = normalize_model_name(body.model)
    agent_mode = normalize_agent_mode(body.agent)
    attachments = [Path(a).name[:120] for a in body.attachments if a]

    if not available_models():
        return JSONResponse({"error": "No model provider is configured. Set GROQ_API_KEY or GEMINI_API_KEY."}, 503)

    agent = get_agent(model)
    config = {"configurable": {"thread_id": thread_id, "agent_mode": agent_mode}}

    if body.regenerate:
        last_user = get_last_user_message(thread_id)
        if last_user is None:
            return JSONResponse({"error": "Nothing to regenerate."}, 400)
        user_message = last_user["content"]
        attachments = last_user["attachments"]
        delete_messages_after(thread_id, last_user["id"])
        rewind_last_turn(agent, config)
    else:
        user_message = body.message.strip()
        if not user_message and attachments:
            user_message = "Please summarize the attached document" + ("s." if len(attachments) > 1 else ".")
        if not user_message:
            return JSONResponse({"error": "Message is required."}, 400)
        create_or_update_conversation(thread_id, user_message, agent_mode)
        save_chat_message(thread_id, "user", user_message, attachments)

    # Tell the model about files attached to this turn so it knows to search them.
    llm_message = user_message
    if attachments:
        llm_message += "\n\n[Attached files in this conversation: " + ", ".join(attachments) + "]"

    def event_generator():
        final_answer = ""
        saved = False
        announced: set[str] = set()
        try:
            yield sse_data({"meta": {"model": model, "agent": agent_mode}})
            for chunk, metadata in agent.stream(
                {"messages": [HumanMessage(content=llm_message)]},
                config=config,
                stream_mode="messages",
            ):
                for name in tool_names_in_chunk(chunk):
                    if name not in announced:
                        announced.add(name)
                        yield sse_data({"status": TOOL_STATUS.get(name, f"Using {name}")})

                if not should_stream_chunk(chunk, metadata):
                    continue
                token = extract_text_from_chunk(chunk)
                if token:
                    final_answer += token
                    yield sse_data({"token": token})

            if not final_answer.strip():
                final_answer = "_(No response was generated. Please try again.)_"
                yield sse_data({"token": final_answer})

            msg_id = save_chat_message(thread_id, "assistant", final_answer)
            saved = True
            yield sse_data({"done": True, "message_id": msg_id})

        except Exception as e:
            log.exception("Chat stream failed")
            yield sse_data({"error": friendly_error(e)})
            yield sse_data({"done": True})
        finally:
            # Client pressed Stop / disconnected: keep what was generated so far.
            if not saved and final_answer.strip():
                try:
                    save_chat_message(thread_id, "assistant", final_answer)
                except Exception:
                    log.exception("Could not save partial answer")

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive", "X-Accel-Buffering": "no"},
    )


def friendly_error(e: Exception) -> str:
    text = str(e)
    low = text.lower()
    if "rate limit" in low or "429" in low or "resource_exhausted" in low:
        return "The model provider is rate-limiting requests. Wait a moment and try again, or switch models."
    if "api key" in low or "401" in low or "unauthorized" in low:
        return "The model provider rejected the API key. Check the server configuration."
    if "context" in low and "length" in low:
        return "This conversation is too long for the model. Start a new chat."
    return f"Something went wrong: {text[:300]}"


if __name__ == "__main__":
    uvicorn.run("app:app", host="0.0.0.0", port=8080, reload=True)
