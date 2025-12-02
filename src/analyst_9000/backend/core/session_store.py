import os
import json
import uuid
from typing import Optional, List, Dict, Any
from contextlib import asynccontextmanager
from analyst_9000.backend.core.logger import get_logger
from analyst_9000.backend.core.constants import ANALYST_LOGGER
from analyst_9000.backend.schemas.db_schemas import ChatSession, ChatSessionSummary, Message
from analyst_9000.backend.helpers.utils import utcnow, load_query

logger = get_logger(ANALYST_LOGGER)


class AsyncSessionStore:
    """
    Async session store supporting both PostgreSQL and SQLite.
    Uses connection pooling for efficient resource management.
    """

    def __init__(
        self,
        connection_url: str,
        pool_size: int = 5,
        max_overflow: int = 10,
    ):
        self.connection_url = connection_url
        self.pool_size = pool_size
        self.max_overflow = max_overflow
        self._pool = None
        self._is_postgres = connection_url.startswith("postgresql")
        self._is_sqlite = connection_url.startswith("sqlite")

    async def init(self) -> "AsyncSessionStore":
        """Initialize connection pool and create tables."""
        if self._is_postgres:
            await self._init_postgres()
        elif self._is_sqlite:
            await self._init_sqlite()
        else:
            raise ValueError(f"Unsupported connection URL: {self.connection_url}")

        await self._create_tables()
        logger.info(f"✅ Session store initialized: {'PostgreSQL' if self._is_postgres else 'SQLite'}")
        return self

    async def _init_postgres(self):
        """Initialize PostgreSQL connection pool using asyncpg."""
        import asyncpg
        
        self._pool = await asyncpg.create_pool(
            self.connection_url,
            min_size=1,
            max_size=self.pool_size + self.max_overflow,
        )

    async def _init_sqlite(self):
        """Initialize SQLite connection using aiosqlite."""
        # Extract file path from URL
        db_path = self.connection_url.replace("sqlite:///", "").replace("sqlite://", "")
        
        # Ensure directory exists
        db_dir = os.path.dirname(db_path)
        if db_dir:
            os.makedirs(db_dir, exist_ok=True)
        
        self._db_path = db_path

    async def _create_tables(self):
        """Create necessary tables."""
        if self._is_postgres:
            create_table_sql = load_query("create_sessions_table_postgres.sql")
            create_index_sql = load_query("create_index_updated_at.sql")
            async with self._pool.acquire() as conn:
                await conn.execute(create_table_sql)
                await conn.execute(create_index_sql)
        else:
            import aiosqlite
            create_table_sql = load_query("create_sessions_table_sqlite.sql")
            create_index_sql = load_query("create_index_updated_at.sql")
            async with aiosqlite.connect(self._db_path) as db:
                await db.execute(create_table_sql)
                await db.execute(create_index_sql)
                await db.commit()

    @asynccontextmanager
    async def _get_connection(self):
        """Get a connection from the pool."""
        if self._is_postgres:
            async with self._pool.acquire() as conn:
                yield conn
        else:
            import aiosqlite
            async with aiosqlite.connect(self._db_path) as db:
                db.row_factory = aiosqlite.Row
                yield db

    def _serialize_json(self, data: Any) -> str:
        """Serialize data to JSON string."""
        if isinstance(data, list):
            return json.dumps([m.model_dump() if hasattr(m, 'model_dump') else m for m in data])
        return json.dumps(data)

    def _deserialize_messages(self, data: Any) -> List[Message]:
        """Deserialize JSON to list of Message objects."""
        if isinstance(data, str):
            data = json.loads(data)
        return [Message(**m) if isinstance(m, dict) else m for m in data]

    async def get_session(self, session_id: str) -> Optional[ChatSession]:
        """Fetch a chat session by ID."""
        async with self._get_connection() as conn:
            if self._is_postgres:
                row = await conn.fetchrow(
                    "SELECT * FROM chat_sessions WHERE id = $1", session_id
                )
                if not row:
                    return None
                return ChatSession(
                    id=row["id"],
                    title=row["title"],
                    messages=self._deserialize_messages(row["messages"]),
                    message_count=row["message_count"],
                    created_at=row["created_at"].isoformat() if hasattr(row["created_at"], 'isoformat') else row["created_at"],
                    updated_at=row["updated_at"].isoformat() if hasattr(row["updated_at"], 'isoformat') else row["updated_at"],
                    is_active=row["is_active"],
                )
            else:
                cursor = await conn.execute(
                    "SELECT * FROM chat_sessions WHERE id = ?", (session_id,)
                )
                row = await cursor.fetchone()
                if not row:
                    return None
                return ChatSession(
                    id=row["id"],
                    title=row["title"],
                    messages=self._deserialize_messages(row["messages"]),
                    message_count=row["message_count"],
                    created_at=row["created_at"],
                    updated_at=row["updated_at"],
                    is_active=bool(row["is_active"]),
                )

    async def create_session(self, session_id: Optional[str] = None) -> ChatSession:
        """Create a new chat session."""
        session_id = session_id or str(uuid.uuid4())
        now_dt = utcnow()
        now_iso = now_dt.isoformat()
        
        session = ChatSession(
            id=session_id,
            created_at=now_iso,
            updated_at=now_iso,
        )

        async with self._get_connection() as conn:
            if self._is_postgres:
                # asyncpg requires datetime objects for TIMESTAMP columns
                await conn.execute(
                    """
                    INSERT INTO chat_sessions (id, title, messages, message_count, created_at, updated_at, is_active)
                    VALUES ($1, $2, $3, $4, $5, $6, $7)
                    """,
                    session.id,
                    session.title,
                    self._serialize_json(session.messages),
                    session.message_count,
                    now_dt,
                    now_dt,
                    session.is_active,
                )
            else:
                await conn.execute(
                    """
                    INSERT INTO chat_sessions (id, title, messages, message_count, created_at, updated_at, is_active)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        session.id,
                        session.title,
                        self._serialize_json(session.messages),
                        session.message_count,
                        session.created_at,
                        session.updated_at,
                        int(session.is_active),
                    ),
                )
                await conn.commit()

        logger.info(f"📝 Created new session: {session_id}")
        return session

    async def update_session(self, session_id: str, updates: Dict[str, Any]) -> Optional[ChatSession]:
        """Update an existing chat session."""
        # Build update query dynamically
        set_clauses = []
        values = []
        
        for key, value in updates.items():
            if key == "messages":
                value = self._serialize_json(value)
            elif key == "updated_at":
                # For PostgreSQL use datetime, for SQLite use string
                if self._is_postgres:
                    value = utcnow()
                else:
                    value = utcnow().isoformat()
            if self._is_postgres:
                set_clauses.append(f"{key} = ${len(values) + 1}")
            else:
                set_clauses.append(f"{key} = ?")
            values.append(value)
        
        # Ensure updated_at is always set
        if "updated_at" not in updates:
            if self._is_postgres:
                set_clauses.append(f"updated_at = ${len(values) + 1}")
                values.append(utcnow())
            else:
                set_clauses.append("updated_at = ?")
                values.append(utcnow().isoformat())

        async with self._get_connection() as conn:
            if self._is_postgres:
                values.append(session_id)
                await conn.execute(
                    f"UPDATE chat_sessions SET {', '.join(set_clauses)} WHERE id = ${len(values)}",
                    *values,
                )
            else:
                values.append(session_id)
                await conn.execute(
                    f"UPDATE chat_sessions SET {', '.join(set_clauses)} WHERE id = ?",
                    values,
                )
                await conn.commit()

        logger.info(f"🔄 Updated session: {session_id}")
        return await self.get_session(session_id)

    async def get_or_create_session(self, session_id: Optional[str] = None) -> ChatSession:
        """Get an existing session or create a new one."""
        if session_id:
            session = await self.get_session(session_id)
            if session:
                return session
        return await self.create_session(session_id)

    async def list_sessions(self, limit: int = 50, offset: int = 0) -> List[ChatSessionSummary]:
        """List chat sessions ordered by last update."""
        async with self._get_connection() as conn:
            if self._is_postgres:
                rows = await conn.fetch(
                    """
                    SELECT id, title, created_at, updated_at, message_count, is_active
                    FROM chat_sessions
                    WHERE is_active = TRUE
                    ORDER BY updated_at DESC
                    LIMIT $1 OFFSET $2
                    """,
                    limit,
                    offset,
                )
                return [
                    ChatSessionSummary(
                        id=row["id"],
                        title=row["title"],
                        created_at=row["created_at"].isoformat() if hasattr(row["created_at"], 'isoformat') else row["created_at"],
                        updated_at=row["updated_at"].isoformat() if hasattr(row["updated_at"], 'isoformat') else row["updated_at"],
                        message_count=row["message_count"],
                        is_active=row["is_active"],
                    )
                    for row in rows
                ]
            else:
                cursor = await conn.execute(
                    """
                    SELECT id, title, created_at, updated_at, message_count, is_active
                    FROM chat_sessions
                    WHERE is_active = 1
                    ORDER BY updated_at DESC
                    LIMIT ? OFFSET ?
                    """,
                    (limit, offset),
                )
                rows = await cursor.fetchall()
                return [
                    ChatSessionSummary(
                        id=row["id"],
                        title=row["title"],
                        created_at=row["created_at"],
                        updated_at=row["updated_at"],
                        message_count=row["message_count"],
                        is_active=bool(row["is_active"]),
                    )
                    for row in rows
                ]

    async def delete_session(self, session_id: str) -> bool:
        """Soft delete a chat session."""
        async with self._get_connection() as conn:
            if self._is_postgres:
                await conn.execute(
                    "UPDATE chat_sessions SET is_active = FALSE, updated_at = $1 WHERE id = $2",
                    utcnow(),
                    session_id,
                )
            else:
                await conn.execute(
                    "UPDATE chat_sessions SET is_active = 0, updated_at = ? WHERE id = ?",
                    (utcnow().isoformat(), session_id),
                )
                await conn.commit()
        
        logger.info(f"🗑️ Deleted session: {session_id}")
        return True

    async def close(self):
        """Close connections."""
        if self._is_postgres and self._pool:
            await self._pool.close()
            logger.info("🔒 Session store pool closed")

