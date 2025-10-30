import os
from typing import List

from fastapi import (
    FastAPI,
    WebSocket,
    WebSocketDisconnect,
    HTTPException,
    status,
    Depends,
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, constr
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import declarative_base, Mapped, mapped_column
from sqlalchemy import String, Text, DateTime, func, select, insert
import asyncio

DATABASE_URL = (
    f"postgresql+asyncpg://{os.getenv('POSTGRES_USER', 'user')}:"
    f"{os.getenv('POSTGRES_PASSWORD', 'password')}@"
    f"{os.getenv('POSTGRES_HOST', 'db')}:5432/"
    f"{os.getenv('POSTGRES_DB', 'chatdb')}"
)

Base = declarative_base()


class Message(Base):
    __tablename__ = "messages"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    author: Mapped[str] = mapped_column(String(255), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    timestamp: Mapped[str] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


# Pydantic schemas
class MessageIn(BaseModel):
    author: constr(strip_whitespace=True, min_length=1, max_length=255)
    message: constr(strip_whitespace=True, min_length=1, max_length=255)


class MessageOut(BaseModel):
    author: str
    message: str
    timestamp: str


# Database setup
engine = create_async_engine(DATABASE_URL, echo=False, future=True)
async_session = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


# Dependency
async def get_session() -> AsyncSession:
    async with async_session() as session:
        yield session


# WebSocket manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        to_remove = []
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception:
                to_remove.append(connection)
        for conn in to_remove:
            self.disconnect(conn)


manager = ConnectionManager()

app = FastAPI()

# CORS for frontend dev
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Adjust for production!
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def on_startup():
    await init_db()


@app.post("/post/send", status_code=200)
async def post_message(msg: MessageIn, session: AsyncSession = Depends(get_session)):
    # Validation is handled by Pydantic
    stmt = insert(Message).values(author=msg.author, message=msg.message)
    await session.execute(stmt)
    await session.commit()

    # Notify all websocket clients
    await manager.broadcast(
        {
            "author": msg.author,
            "message": msg.message,
            # No timestamp here, clients can refresh or reload for full data
        }
    )
    return JSONResponse(content={"detail": "Message sent"}, status_code=200)


@app.get("/get/msg", response_model=List[MessageOut])
async def get_messages(session: AsyncSession = Depends(get_session)):
    stmt = select(Message).order_by(Message.timestamp.asc())
    result = await session.execute(stmt)
    messages = result.scalars().all()
    return [
        MessageOut(
            author=m.author,
            message=m.message,
            timestamp=m.timestamp.isoformat() if m.timestamp else "",
        )
        for m in messages
    ]


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            # Keep connection alive, but don't expect messages from client
            await asyncio.sleep(60)
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception:
        manager.disconnect(websocket)
