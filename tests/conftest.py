"""Test setup: isolated data dirs and a scripted fake LLM (no API keys or network needed)."""

import json
import os
import re
import sys
import tempfile
from pathlib import Path

# Must be set before the app modules are imported.
_TMP = Path(tempfile.mkdtemp(prefix="kaleemgpt-tests-"))
os.environ["DATA_DIR"] = str(_TMP / "data")
os.environ["UPLOAD_DIR"] = str(_TMP / "uploads")
os.environ["GROQ_API_KEY"] = "test-key"
os.environ["GEMINI_API_KEY"] = "test-key"
os.environ.pop("TAVILY_API_KEY", None)
os.environ.pop("GROQ_MODEL", None)

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, AIMessageChunk
from langchain_core.outputs import ChatGeneration, ChatGenerationChunk, ChatResult
from pydantic import Field


class FakeLLM(BaseChatModel):
    """Returns scripted AIMessages in order and streams them like a real provider."""

    responses: list = Field(default_factory=list)
    calls: list = Field(default_factory=list)

    @property
    def _llm_type(self) -> str:
        return "fake"

    def bind_tools(self, tools, **kwargs):
        return self

    def _next(self, messages):
        self.calls.append(messages)
        msg = self.responses.pop(0)
        return AIMessage(content=msg) if isinstance(msg, str) else msg

    def _generate(self, messages, stop=None, run_manager=None, **kwargs):
        return ChatResult(generations=[ChatGeneration(message=self._next(messages))])

    def _stream(self, messages, stop=None, run_manager=None, **kwargs):
        msg = self._next(messages)
        if msg.tool_calls:
            chunk = ChatGenerationChunk(message=AIMessageChunk(
                content="",
                tool_call_chunks=[
                    {"name": tc["name"], "args": json.dumps(tc["args"]), "id": tc["id"], "index": i}
                    for i, tc in enumerate(msg.tool_calls)
                ],
            ))
            if run_manager:
                run_manager.on_llm_new_token("", chunk=chunk)
            yield chunk
            return
        for piece in re.split(r"(\s+)", msg.content):
            if piece:
                chunk = ChatGenerationChunk(message=AIMessageChunk(content=piece))
                if run_manager:
                    run_manager.on_llm_new_token(piece, chunk=chunk)
                yield chunk


@pytest.fixture(scope="session")
def app_module():
    import app as app_module

    return app_module


@pytest.fixture()
def fake_llm(app_module):
    import agent

    llm = FakeLLM()
    agent._AGENT_CACHE.clear()
    agent._AGENT_CACHE[agent.default_model()] = agent.build_agent("fake", llm=llm)
    yield llm
    agent._AGENT_CACHE.clear()


@pytest.fixture()
def client(app_module, fake_llm):
    from fastapi.testclient import TestClient

    with TestClient(app_module.app) as c:
        yield c


@pytest.fixture()
def fake_vectorstore(tmp_path):
    from langchain_chroma import Chroma
    from langchain_core.embeddings import DeterministicFakeEmbedding

    import rag

    rag._vectorstore = Chroma(
        collection_name="test_docs",
        embedding_function=DeterministicFakeEmbedding(size=32),
        persist_directory=str(tmp_path / "chroma"),
    )
    yield rag._vectorstore
    rag._vectorstore = None


def parse_sse(text: str) -> list[dict]:
    events = []
    for block in text.split("\n\n"):
        for line in block.splitlines():
            if line.startswith("data: "):
                events.append(json.loads(line[6:]))
    return events
