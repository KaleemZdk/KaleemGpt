import ast
import math
import operator
import os
import re
from functools import lru_cache

from langchain_core.runnables import RunnableConfig
from langchain_core.tools import tool

from database import (  # importing database also loads .env via config
    save_memory,
    search_memory,
)
from rag import retrieve_from_rag


def _thread_id(cfg: RunnableConfig | None) -> str:
    """The conversation id travels with each run's config.

    The previous global CURRENT_THREAD_ID was shared by every request, so two
    people chatting at once could read each other's documents and memories.
    """
    return ((cfg or {}).get("configurable") or {}).get("thread_id", "default")


# ----------------------------------------------------------------------------
# Web search
# ----------------------------------------------------------------------------

@lru_cache(maxsize=1)
def _tavily():
    from tavily import TavilyClient

    return TavilyClient(api_key=os.getenv("TAVILY_API_KEY"))


def web_search_available() -> bool:
    return bool(os.getenv("TAVILY_API_KEY", "").strip())


@tool
def web_search(query: str) -> str:
    """Search the web for current information, news, prices, or facts you don't
    already know. Returns the top results with titles, URLs, and snippets."""
    if not web_search_available():
        return "Web search is not configured on this server (TAVILY_API_KEY missing)."
    try:
        results = _tavily().search(query=query, max_results=5)
    except Exception as e:
        return f"Search failed: {e}"

    out = [
        f"Title: {r.get('title', '')}\nURL: {r.get('url', '')}\nSnippet: {(r.get('content') or '')[:400]}"
        for r in results.get("results", [])
    ]
    return "\n----\n".join(out) if out else "No results found."


# ----------------------------------------------------------------------------
# Calculator (safe AST evaluator, no eval())
# ----------------------------------------------------------------------------

_ALLOWED_OPS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Pow: operator.pow,
    ast.Mod: operator.mod,
    ast.USub: operator.neg,
    ast.UAdd: operator.pos,
}
_ALLOWED_FUNCS = {
    "sqrt": math.sqrt, "abs": abs, "round": round, "log": math.log,
    "log10": math.log10, "sin": math.sin, "cos": math.cos, "tan": math.tan,
}
_ALLOWED_NAMES = {"pi": math.pi, "e": math.e}


def _safe_eval(node):
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return node.value
    if isinstance(node, ast.Name) and node.id in _ALLOWED_NAMES:
        return _ALLOWED_NAMES[node.id]
    if isinstance(node, ast.BinOp) and type(node.op) in _ALLOWED_OPS:
        left, right = _safe_eval(node.left), _safe_eval(node.right)
        if isinstance(node.op, ast.Pow) and abs(right) > 1000:
            raise ValueError("Exponent too large.")
        return _ALLOWED_OPS[type(node.op)](left, right)
    if isinstance(node, ast.UnaryOp) and type(node.op) in _ALLOWED_OPS:
        return _ALLOWED_OPS[type(node.op)](_safe_eval(node.operand))
    if (
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id in _ALLOWED_FUNCS
        and not node.keywords
    ):
        return _ALLOWED_FUNCS[node.func.id](*[_safe_eval(a) for a in node.args])
    raise ValueError("Unsupported or unsafe expression.")


@tool
def calculator(expression: str) -> str:
    """Evaluate a math expression, e.g. '12 * (3 + 4) / 2' or 'sqrt(144) + 2**10'.
    Supports + - * / // ** %, parentheses, pi, e and sqrt/abs/round/log/log10/sin/cos/tan."""
    try:
        expr = expression.replace("×", "*").replace("÷", "/").replace("^", "**")
        expr = re.sub(r"(?<=\d),(?=\d{3}(?!\d))", "", expr)  # 4,234 -> 4234, keeps round(x, 2)
        result = _safe_eval(ast.parse(expr, mode="eval").body)
        if isinstance(result, float) and result.is_integer() and abs(result) < 1e15:
            result = int(result)
        return str(result)
    except Exception as e:
        return f"Could not evaluate '{expression}': {e}"


# ----------------------------------------------------------------------------
# Documents (RAG)
# ----------------------------------------------------------------------------

@tool
def search_uploaded_documents(query: str, config: RunnableConfig) -> str:
    """Search the documents the user uploaded in this conversation (PDF, DOCX, TXT, code, CSV...).
    Use this whenever the user asks about an uploaded file. The query must be a specific
    search phrase based on the user's question. For vague requests like "summarize my file"
    use the query "summary of the document"."""
    query = (query or "").strip() or "summary of the document"
    try:
        return retrieve_from_rag(query=query, thread_id=_thread_id(config))
    except Exception as e:
        return f"Document search failed: {e}"


# ----------------------------------------------------------------------------
# Memory
# ----------------------------------------------------------------------------

@tool
def remember_this(memory: str, config: RunnableConfig) -> str:
    """Save an important fact or preference about the user to long-term memory
    (available in all future conversations). Use when the user asks you to remember something.
    Write the memory as a short self-contained sentence, e.g. "The user's name is Kaleem"."""
    return save_memory(thread_id=_thread_id(config), memory=memory)


@tool
def recall_memory(query: str) -> str:
    """Recall saved long-term memories about the user (name, preferences, facts they asked
    you to remember). Use when the user asks what you know or remember about them."""
    return search_memory(query=query)


tools = [
    calculator,
    search_uploaded_documents,
    remember_this,
    recall_memory,
    web_search,
]

TOOL_STATUS = {
    "web_search": "Searching the web",
    "search_uploaded_documents": "Reading your documents",
    "calculator": "Calculating",
    "remember_this": "Saving to memory",
    "recall_memory": "Checking memory",
}
