import json
import re
from datetime import UTC, datetime

from sqlalchemy import (
    Column,
    DateTime,
    Integer,
    String,
    Text,
    create_engine,
    event,
    inspect,
    text,
)
from sqlalchemy.orm import declarative_base, sessionmaker

from config import DATABASE_URL

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},
    pool_pre_ping=True,
)


@event.listens_for(engine, "connect")
def _sqlite_pragmas(dbapi_conn, _record):
    # WAL lets reads proceed while a stream is writing; NORMAL sync is safe with WAL.
    cur = dbapi_conn.cursor()
    cur.execute("PRAGMA journal_mode=WAL")
    cur.execute("PRAGMA synchronous=NORMAL")
    cur.close()


SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)
Base = declarative_base()

PLACEHOLDER_TITLES = {"New Chat", "Uploaded document"}


def utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def iso(dt: datetime | None) -> str | None:
    """Serialize naive-UTC datetimes with an explicit Z so browsers don't treat them as local time."""
    if dt is None:
        return None
    return dt.replace(microsecond=0).isoformat() + "Z"


class Conversation(Base):
    __tablename__ = "conversations"

    id = Column(Integer, primary_key=True, index=True)
    thread_id = Column(String, unique=True, index=True)
    title = Column(String, default="New Chat")
    agent = Column(String, default="general")
    created_at = Column(DateTime, default=utcnow)
    updated_at = Column(DateTime, default=utcnow, index=True)


class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id = Column(Integer, primary_key=True, index=True)
    thread_id = Column(String, index=True)
    role = Column(String)
    content = Column(Text)
    attachments = Column(Text, default="[]")
    created_at = Column(DateTime, default=utcnow)


class LongTermMemory(Base):
    __tablename__ = "long_term_memory"

    id = Column(Integer, primary_key=True, index=True)
    thread_id = Column(String, index=True)
    memory = Column(Text)
    created_at = Column(DateTime, default=utcnow)


def _add_missing_columns():
    """Tiny migration step: create_all() never alters existing tables."""
    wanted = {
        "conversations": {"agent": "VARCHAR DEFAULT 'general'"},
        "chat_messages": {"attachments": "TEXT DEFAULT '[]'"},
    }
    insp = inspect(engine)
    with engine.begin() as conn:
        for table, cols in wanted.items():
            existing = {c["name"] for c in insp.get_columns(table)}
            for name, ddl in cols.items():
                if name not in existing:
                    conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {name} {ddl}"))


def init_db():
    Base.metadata.create_all(bind=engine)
    _add_missing_columns()


def make_title(message: str) -> str:
    clean = re.sub(r"\s+", " ", message or "").strip()
    if not clean:
        return "New Chat"
    return clean[:50] + ("…" if len(clean) > 50 else "")


# ----------------------------------------------------------------------------
# Conversations
# ----------------------------------------------------------------------------

def _conversation_dict(c: Conversation) -> dict:
    return {
        "thread_id": c.thread_id,
        "title": c.title,
        "agent": c.agent or "general",
        "created_at": iso(c.created_at),
        "updated_at": iso(c.updated_at),
    }


def create_or_update_conversation(thread_id: str, first_message: str | None = None, agent: str | None = None):
    """Create the conversation if needed; give it a real title once a real message arrives."""
    with SessionLocal() as db:
        conv = db.query(Conversation).filter(Conversation.thread_id == thread_id).first()
        now = utcnow()
        if conv is None:
            conv = Conversation(
                thread_id=thread_id,
                title=make_title(first_message) if first_message else "New Chat",
                agent=agent or "general",
                created_at=now,
                updated_at=now,
            )
            db.add(conv)
        else:
            if first_message and conv.title in PLACEHOLDER_TITLES:
                conv.title = make_title(first_message)
            if agent:
                conv.agent = agent
            conv.updated_at = now
        db.commit()
        return _conversation_dict(conv)


def list_conversations() -> list[dict]:
    with SessionLocal() as db:
        rows = db.query(Conversation).order_by(Conversation.updated_at.desc()).all()
        return [_conversation_dict(c) for c in rows]


def rename_conversation(thread_id: str, title: str) -> dict | None:
    with SessionLocal() as db:
        conv = db.query(Conversation).filter(Conversation.thread_id == thread_id).first()
        if conv is None:
            return None
        conv.title = title.strip()[:120] or conv.title
        db.commit()
        return _conversation_dict(conv)


def delete_conversation(thread_id: str) -> bool:
    with SessionLocal() as db:
        deleted = db.query(Conversation).filter(Conversation.thread_id == thread_id).delete()
        db.query(ChatMessage).filter(ChatMessage.thread_id == thread_id).delete()
        db.commit()
        return bool(deleted)


def all_thread_ids() -> list[str]:
    with SessionLocal() as db:
        return [t for (t,) in db.query(Conversation.thread_id).all()]


# ----------------------------------------------------------------------------
# Messages
# ----------------------------------------------------------------------------

def save_chat_message(thread_id: str, role: str, content: str, attachments: list[str] | None = None) -> int:
    with SessionLocal() as db:
        msg = ChatMessage(
            thread_id=thread_id,
            role=role,
            content=content,
            attachments=json.dumps(attachments or []),
            created_at=utcnow(),
        )
        db.add(msg)
        db.query(Conversation).filter(Conversation.thread_id == thread_id).update(
            {Conversation.updated_at: utcnow()}
        )
        db.commit()
        return msg.id


def get_chat_history(thread_id: str) -> list[dict]:
    with SessionLocal() as db:
        rows = (
            db.query(ChatMessage)
            .filter(ChatMessage.thread_id == thread_id)
            .order_by(ChatMessage.id.asc())
            .all()
        )
        out = []
        for m in rows:
            try:
                attachments = json.loads(m.attachments or "[]")
            except ValueError:
                attachments = []
            out.append({
                "id": m.id,
                "role": m.role,
                "content": m.content,
                "attachments": attachments,
                "created_at": iso(m.created_at),
            })
        return out


def get_last_user_message(thread_id: str) -> dict | None:
    with SessionLocal() as db:
        m = (
            db.query(ChatMessage)
            .filter(ChatMessage.thread_id == thread_id, ChatMessage.role == "user")
            .order_by(ChatMessage.id.desc())
            .first()
        )
        if m is None:
            return None
        try:
            attachments = json.loads(m.attachments or "[]")
        except ValueError:
            attachments = []
        return {"id": m.id, "content": m.content, "attachments": attachments}


def delete_messages_after(thread_id: str, message_id: int) -> int:
    """Remove every message newer than message_id (used when regenerating a reply)."""
    with SessionLocal() as db:
        n = (
            db.query(ChatMessage)
            .filter(ChatMessage.thread_id == thread_id, ChatMessage.id > message_id)
            .delete()
        )
        db.commit()
        return n


# ----------------------------------------------------------------------------
# Long-term memory (shared across conversations — that's what makes it long-term)
# ----------------------------------------------------------------------------

def save_memory(thread_id: str, memory: str) -> str:
    memory = (memory or "").strip()
    if not memory:
        return "Nothing to save."
    with SessionLocal() as db:
        exists = db.query(LongTermMemory).filter(LongTermMemory.memory == memory).first()
        if exists:
            return "I already remember that."
        db.add(LongTermMemory(thread_id=thread_id, memory=memory, created_at=utcnow()))
        db.commit()
    return "Memory saved successfully."


def search_memory(query: str, limit: int = 20) -> str:
    with SessionLocal() as db:
        base = db.query(LongTermMemory).order_by(LongTermMemory.created_at.desc())
        words = [w for w in re.findall(r"\w+", (query or "").lower()) if len(w) > 2]

        matches = []
        if words:
            from sqlalchemy import or_

            matches = base.filter(or_(*[LongTermMemory.memory.ilike(f"%{w}%") for w in words])).limit(limit).all()

        if not matches:
            # Memories are short; returning the most recent ones lets the model decide relevance.
            matches = base.limit(limit).all()

        if not matches:
            return "No saved memories yet."
        return "\n".join(f"- {m.memory}" for m in matches)


def list_memories() -> list[dict]:
    with SessionLocal() as db:
        rows = db.query(LongTermMemory).order_by(LongTermMemory.created_at.desc()).all()
        return [{"id": m.id, "memory": m.memory, "created_at": iso(m.created_at)} for m in rows]


def delete_memory(memory_id: int) -> bool:
    with SessionLocal() as db:
        n = db.query(LongTermMemory).filter(LongTermMemory.id == memory_id).delete()
        db.commit()
        return bool(n)
