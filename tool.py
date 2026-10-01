import ast
from dotenv import load_dotenv
from langchain_core.tools import tool 
load_dotenv()
import operator
from tavily import TavilyClient
from database import save_memory,search_memory
from rag import retrieve_from_rag
import os 


CURRENT_THREAD_ID = "default"

def set_current_thread_id(thread_id: str):
    global CURRENT_THREAD_ID
    CURRENT_THREAD_ID = thread_id

tavily = TavilyClient(api_key=os.getenv("TAVILY_API_KEY"))

#Web search 
@tool
def web_search(query: str) -> str:
    """Search the web for current information, news, or facts you don't
    already know. Returns the top results with titles, URLs, and snippets."""
 
    try:
        results = tavily.search(query=query, max_results=5)
    except Exception as e:
        return f"Search failed: {e}"
 
    out = []
    for r in results.get("results", []):
        out.append(f"Title:{r['title']}\nURL:{r['url']}\nSnippet:{r['content'][:300]}\n")
 
    return "\n----\n".join(out) if out else "No results found."
 
 
#Calculator 
_ALLOWED_OPS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.Pow: operator.pow,
    ast.Mod: operator.mod,
    ast.USub: operator.neg,
    ast.UAdd: operator.pos,
}
 
 
def _safe_eval(node):
    if isinstance(node, ast.Constant):
        if isinstance(node.value, (int, float)):
            return node.value
        raise ValueError("Only numeric constants are allowed.")
    if isinstance(node, ast.BinOp) and type(node.op) in _ALLOWED_OPS:
        return _ALLOWED_OPS[type(node.op)](_safe_eval(node.left), _safe_eval(node.right))
    if isinstance(node, ast.UnaryOp) and type(node.op) in _ALLOWED_OPS:
        return _ALLOWED_OPS[type(node.op)](_safe_eval(node.operand))
    raise ValueError("Unsupported or unsafe expression.")
 
 
@tool
def calculator(expression: str) -> str:
    """Evaluate a math expression, e.g. '12 * (3 + 4) / 2'. Supports +, -,
    *, /, **, and %. Does not support raw eval — unsafe expressions are
    rejected."""
 
    try:
        tree = ast.parse(expression, mode="eval")
        result = _safe_eval(tree.body)
        return str(result)
    except Exception as e:
        return f"Could not evaluate '{expression}': {e}"

@tool
def search_uploaded_documents(query: str) -> str:
    """
    Search the user's uploaded documents (PDF, DOCX, TXT, notes, files) for relevant information.
    Use this when the user asks about an uploaded file or document.
    The query must be a specific search phrase based on the user's question, never empty.
    If the request is vague (for example "read my file" or "this is my doc"),
    use the query "summary of the document".
    """

    # Vague messages can make the model pass an empty query, which Gemini's embedding API rejects
    if not query or not query.strip():
        query = "summary of the document"

    return retrieve_from_rag(
        query=query.strip(),
        thread_id=CURRENT_THREAD_ID
    )



@tool
def remember_this(memory: str) -> str:
    """
    Save an important user preference or fact into long-term memory.
    Use this when the user asks you to remember something.
    """
    return save_memory(
        thread_id=CURRENT_THREAD_ID,
        memory=memory
    )

@tool 
def recall_memory(query: str)->str:

    """
    Recall saved long-term memories about the user of this conversation
    """
    return search_memory(
        thread_id = CURRENT_THREAD_ID,
        query = query

    )

tools = [
    calculator,
    search_uploaded_documents,
    remember_this,
    recall_memory,
    web_search,
]