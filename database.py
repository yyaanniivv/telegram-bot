"""Database models and session management for Magnet2Torrent Bot."""
import os
from datetime import date, datetime
from typing import Optional

from sqlalchemy import (
    BigInteger,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    create_engine,
    select,
)
from sqlalchemy.orm import (
    DeclarativeBase,
    Mapped,
    mapped_column,
    relationship,
    sessionmaker,
)
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)


class Base(DeclarativeBase):
    """Base class for all models."""
    pass


class ApprovedUser(Base):
    """Approved users from APPROVED_IDS env var."""
    __tablename__ = "approved_users"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False)
    username: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    first_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    last_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    # Relationships
    searches: Mapped[list["SearchHistory"]] = relationship(back_populates="user")
    torrents: Mapped[list["CreatedTorrent"]] = relationship(back_populates="user")

    def __repr__(self) -> str:
        return f"<ApprovedUser(id={self.id}, username={self.username})>"


class SearchHistory(Base):
    """History of inline searches performed by users."""
    __tablename__ = "search_history"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("approved_users.id"), nullable=False, index=True
    )
    query: Mapped[str] = mapped_column(String(500), nullable=False)
    results_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    # Relationships
    user: Mapped["ApprovedUser"] = relationship(back_populates="searches")
    results: Mapped[list["SearchResult"]] = relationship(back_populates="search_history", cascade="all, delete-orphan")

    # Indexes
    __table_args__ = (
        UniqueConstraint("user_id", "query", "created_at", name="uq_search_history"),
    )

    def __repr__(self) -> str:
        return f"<SearchHistory(id={self.id}, user_id={self.user_id}, query={self.query[:30]})>"


class SearchResult(Base):
    """Individual search results stored for later torrent creation."""
    __tablename__ = "search_results"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    search_history_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("search_history.id"), nullable=False, index=True
    )
    btih: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    magnet_link: Mapped[str] = mapped_column(Text, nullable=False)
    size_bytes: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    size_human: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    seeders: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    leechers: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    uploaded_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationship
    search_history: Mapped["SearchHistory"] = relationship(back_populates="results")

    __table_args__ = (
        UniqueConstraint("search_history_id", "btih", name="uq_search_result"),
    )

    def __repr__(self) -> str:
        return f"<SearchResult(id={self.id}, btih={self.btih[:8]}..., title={self.title[:30]})>"


class CreatedTorrent(Base):
    """Record of torrent files created by users."""
    __tablename__ = "created_torrents"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("approved_users.id"), nullable=False, index=True
    )
    btih: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    magnet_link: Mapped[str] = mapped_column(Text, nullable=False)
    search_term: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    file_path: Mapped[str] = mapped_column(String(500), nullable=False)
    file_size_bytes: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    # Metadata from search result
    title: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    size_bytes: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    seeders: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    leechers: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    uploaded_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    # Relationships
    user: Mapped["ApprovedUser"] = relationship(back_populates="torrents")

    def __repr__(self) -> str:
        return f"<CreatedTorrent(id={self.id}, btih={self.btih[:8]}..., user_id={self.user_id})>"


class AnalyticsEvent(Base):
    """Analytics events for usage tracking."""
    __tablename__ = "analytics_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[Optional[int]] = mapped_column(
        BigInteger, ForeignKey("approved_users.id"), nullable=True, index=True
    )
    event_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    event_data: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    def __repr__(self) -> str:
        return f"<AnalyticsEvent(id={self.id}, type={self.event_type}, user_id={self.user_id})>"


class DatabaseManager:
    """Manages database connections and operations."""

    def __init__(self, database_url: str):
        self.database_url = database_url
        self._engine = None
        self._async_session_factory = None

    def init_sync_engine(self):
        """Initialize synchronous engine for migrations."""
        self._engine = create_engine(self.database_url, echo=False)
        return self._engine

    def init_async_engine(self):
        """Initialize asynchronous engine for runtime operations."""
        self._engine = create_async_engine(self.database_url, echo=False)
        self._async_session_factory = async_sessionmaker(
            self._engine, class_=AsyncSession, expire_on_commit=False
        )
        return self._engine

    async def create_tables(self):
        """Create all tables (for init, not for migrations)."""
        if self._engine is None:
            self.init_async_engine()
        async with self._engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    async def drop_tables(self):
        """Drop all tables (for testing)."""
        if self._engine is None:
            self.init_async_engine()
        async with self._engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)

    def get_session(self) -> AsyncSession:
        """Get a new async session."""
        if self._async_session_factory is None:
            self.init_async_engine()
        return self._async_session_factory()

    async def close(self):
        """Close the database connection."""
        if self._engine:
            await self._engine.dispose()


def get_database_url() -> str:
    """Get database URL from environment."""
    output_dir = os.environ.get("OUTPUT_DIR", "./output")
    db_path = os.path.join(output_dir, "bot.db")
    return f"sqlite+aiosqlite:///{db_path}"


def get_sync_database_url() -> str:
    """Get synchronous database URL for migrations."""
    output_dir = os.environ.get("OUTPUT_DIR", "./output")
    db_path = os.path.join(output_dir, "bot.db")
    return f"sqlite:///{db_path}"


# Global database manager instance
db_manager: Optional[DatabaseManager] = None


def init_database() -> DatabaseManager:
    """Initialize global database manager."""
    global db_manager
    db_url = get_database_url()
    db_manager = DatabaseManager(db_url)
    db_manager.init_async_engine()
    return db_manager


async def get_db_session() -> AsyncSession:
    """Get a database session (for dependency injection)."""
    if db_manager is None:
        init_database()
    return db_manager.get_session()