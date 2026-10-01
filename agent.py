import os 
from pathlib import Path 
import sqlite3
from dotenv import load_dotenv
import certifi 

load_dotenv()

os.environ["SSL_CERT_FILE"] = certifi.where()
os.environ["REQUESTS_CA_BUNDLE"] = certifi.where()

from langchain_groq import ChatGroq
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import SystemMessage
from langgraph.graph import StateGraph,START,MessagesState
from langgraph.prebuilt import ToolNode,tools_condition
from langgraph.checkpoint.sqlite import SqliteSaver
from tool import tools
Path("data").mkdir(exist_ok=True)

DEFAULT_MODEL = os.getenv("GROQ_MODEL", "openai/gpt-oss-20b")

ALLOWED_MODELS = {
    "openai/gpt-oss-20b",
    "openai/gpt-oss-120b",
}
SYSTEM_PROMPT = """
You are a helpful Agentic AI assistant named BappyGPT similar to ChatGPT.

You can:
1. Answer normal questions.
2. Use tools when needed.
3. Search uploaded documents using the RAG tool.
4. Search the web for current information using Tavily Search.
5. Recall important user information using the memory tool.
6. Use calculator for math.

Rules:
- If the user asks about latest news, current events, recent updates, today's information, current prices, use web search.
- If the user asks about an uploaded document, use search_uploaded_documents.
- If the user asks you to remember something, use memory.
- If the user asks about previous preferences or saved facts, use recall_memory.
- Use calculator for math questions.
- When using web search, summarize the answer and mention that the answer is based on web search results.
- Be clear, helpful, and concise.
"""

def normalize_model_name(model_name:str):


    if not model_name:
        return DEFAULT_MODEL
    
    model_name = model_name.strip()

    if model_name not in ALLOWED_MODELS:
        return DEFAULT_MODEL
    
    return model_name


def build_agent(model_name: str):

    """
    Build one langgraph agent for a selected gemini model.
    """

    selected_model = normalize_model_name(model_name)

#     llm = ChatGoogleGenerativeAI(
#     model=selected_model,
#     streaming=True,
#     google_api_key=os.getenv("GEMINI_API_KEY")
# )
    llm = ChatGroq(
        model=selected_model,
        groq_api_key=os.getenv("GROQ_API_KEY"),
        streaming=True,
    )

    llm_with_tools = llm.bind_tools(tools)

    def chatbot_node(state: MessagesState):
        messages = [SystemMessage(content=SYSTEM_PROMPT)] + state["messages"]
        response = llm_with_tools.invoke(messages)
        return {"messages": [response]}
    
    tool_node = ToolNode(tools)

    workflow = StateGraph(MessagesState)

    workflow.add_node("chatbot",chatbot_node)
    workflow.add_node("tools",tool_node)

    workflow.add_edge(START,"chatbot")
    workflow.add_conditional_edges("chatbot",tools_condition)
    workflow.add_edge("tools","chatbot")

    conn = sqlite3.connect(
        "data/langgarph_checkpoints.sqlite",
        check_same_thread= False
    )

    checkpointer = SqliteSaver(conn)

    return workflow.compile(checkpointer=checkpointer)

_AGENT_CACHE = {}


def get_agent(model_name: str | None = None):
    """
    Return cached LangGraph agent for selected model.
    If not created yet, create it once and reuse it.
    """

    selected_model = normalize_model_name(model_name)

    if selected_model not in _AGENT_CACHE:
        _AGENT_CACHE[selected_model] = build_agent(selected_model)

    return _AGENT_CACHE[selected_model]

