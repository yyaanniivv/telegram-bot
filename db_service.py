"""Database service layer for common operations."""
import json
from datetime import datetime
from typing import Optional, List, Dict, Any

from sqlalchemy import select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession

from database import (
    ApprovedUser,
    SearchHistory,
    CreatedTorrent,
    AnalyticsEvent,
    get_db_session,
    init_database,
)


class DatabaseService:
    """Service layer for database operations."""

    def __init__(self):
        self._initialized = False

    async def initialize(self):
        """Initialize database and create tables if needed."""
        if not self._initialized:
            init_database()
            await self._sync_approved_users()
            self._initialized = True

    async def _sync_approved_users(self):
        """Sync approved users from APPROVED_IDS env var to database."""
        import os
        approved_ids_str = os.environ.get("APPROVED_IDS", "")
        if not approved_ids_str:
            return

        approved_ids = [int(x.strip()) for x in approved_ids_str.split(",") if x.strip()]
        session = await get_db_session()
        async with session:
            for user_id in approved_ids:
                # Check if user exists
                stmt = select(ApprovedUser).where(ApprovedUser.id == user_id)
                result = await session.execute(stmt)
                user = result.scalar_one_or_none()

                if user is None:
                    # Create new approved user
                    user = ApprovedUser(id=user_id, is_active=True)
                    session.add(user)
            await session.commit()

    # --- Approved Users ---

    async def get_approved_user(self, user_id: int) -> Optional[ApprovedUser]:
        """Get approved user by ID."""
        session = await get_db_session()
        async with session:
            stmt = select(ApprovedUser).where(ApprovedUser.id == user_id)
            result = await session.execute(stmt)
            return result.scalar_one_or_none()

    async def is_user_approved(self, user_id: int) -> bool:
        """Check if user is in approved list."""
        user = await self.get_approved_user(user_id)
        return user is not None and user.is_active

    async def update_user_info(
        self, user_id: int, username: Optional[str] = None,
        first_name: Optional[str] = None, last_name: Optional[str] = None
    ) -> Optional[ApprovedUser]:
        """Update user info from Telegram."""
        session = await get_db_session()
        async with session:
            stmt = select(ApprovedUser).where(ApprovedUser.id == user_id)
            result = await session.execute(stmt)
            user = result.scalar_one_or_none()

            if user:
                if username is not None:
                    user.username = username
                if first_name is not None:
                    user.first_name = first_name
                if last_name is not None:
                    user.last_name = last_name
                user.updated_at = datetime.utcnow()
                await session.commit()
                await session.refresh(user)
            return user

    # --- Search History ---

    async def record_search(
        self, user_id: int, query: str, results_count: int
    ) -> SearchHistory:
        """Record a search query."""
        session = await get_db_session()
        async with session:
            search = SearchHistory(
                user_id=user_id,
                query=query,
                results_count=results_count,
            )
            session.add(search)
            await session.commit()
            await session.refresh(search)
            return search

    async def get_user_search_history(
        self, user_id: int, limit: int = 50
    ) -> List[SearchHistory]:
        """Get search history for a user."""
        session = await get_db_session()
        async with session:
            stmt = (
                select(SearchHistory)
                .where(SearchHistory.user_id == user_id)
                .order_by(desc(SearchHistory.created_at))
                .limit(limit)
            )
            result = await session.execute(stmt)
            return list(result.scalars().all())

    async def get_popular_searches(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get most popular search queries."""
        session = await get_db_session()
        async with session:
            stmt = (
                select(SearchHistory.query, func.count(SearchHistory.id).label("count"))
                .group_by(SearchHistory.query)
                .order_by(desc("count"))
                .limit(limit)
            )
            result = await session.execute(stmt)
            return [{"query": row[0], "count": row[1]} for row in result.all()]

    # --- Created Torrents ---

    async def record_created_torrent(
        self,
        user_id: int,
        btih: str,
        magnet_link: str,
        search_term: Optional[str],
        filename: str,
        file_path: str,
        file_size_bytes: Optional[int] = None,
    ) -> CreatedTorrent:
        """Record a created torrent file."""
        session = await get_db_session()
        async with session:
            torrent = CreatedTorrent(
                user_id=user_id,
                btih=btih,
                magnet_link=magnet_link,
                search_term=search_term,
                filename=filename,
                file_path=file_path,
                file_size_bytes=file_size_bytes,
            )
            session.add(torrent)
            await session.commit()
            await session.refresh(torrent)
            return torrent

    async def get_user_torrents(
        self, user_id: int, limit: int = 50
    ) -> List[CreatedTorrent]:
        """Get torrents created by a user."""
        session = await get_db_session()
        async with session:
            stmt = (
                select(CreatedTorrent)
                .where(CreatedTorrent.user_id == user_id)
                .order_by(desc(CreatedTorrent.created_at))
                .limit(limit)
            )
            result = await session.execute(stmt)
            return list(result.scalars().all())

    async def get_torrent_by_btih(self, btih: str) -> Optional[CreatedTorrent]:
        """Get torrent by BTIH."""
        session = await get_db_session()
        async with session:
            stmt = select(CreatedTorrent).where(CreatedTorrent.btih == btih)
            result = await session.execute(stmt)
            return result.scalar_one_or_none()

    # --- Analytics ---

    async def record_event(
        self,
        event_type: str,
        user_id: Optional[int] = None,
        event_data: Optional[Dict[str, Any]] = None,
    ) -> AnalyticsEvent:
        """Record an analytics event."""
        session = await get_db_session()
        async with session:
            event = AnalyticsEvent(
                user_id=user_id,
                event_type=event_type,
                event_data=json.dumps(event_data) if event_data else None,
            )
            session.add(event)
            await session.commit()
            await session.refresh(event)
            return event

    async def get_event_counts(
        self, event_type: Optional[str] = None, days: int = 7
    ) -> Dict[str, int]:
        """Get event counts for the last N days."""
        from datetime import timedelta
        cutoff = datetime.utcnow() - timedelta(days=days)

        session = await get_db_session()
        async with session:
            stmt = (
                select(AnalyticsEvent.event_type, func.count(AnalyticsEvent.id))
                .where(AnalyticsEvent.created_at >= cutoff)
            )
            if event_type:
                stmt = stmt.where(AnalyticsEvent.event_type == event_type)

            stmt = stmt.group_by(AnalyticsEvent.event_type)
            result = await session.execute(stmt)
            return {row[0]: row[1] for row in result.all()}

    async def get_user_activity(self, user_id: int, days: int = 30) -> Dict[str, int]:
        """Get activity summary for a user."""
        from datetime import timedelta
        cutoff = datetime.utcnow() - timedelta(days=days)

        session = await get_db_session()
        async with session:
            # Search count
            search_stmt = select(func.count(SearchHistory.id)).where(
                SearchHistory.user_id == user_id,
                SearchHistory.created_at >= cutoff,
            )
            search_result = await session.execute(search_stmt)
            search_count = search_result.scalar_one()

            # Torrent count
            torrent_stmt = select(func.count(CreatedTorrent.id)).where(
                CreatedTorrent.user_id == user_id,
                CreatedTorrent.created_at >= cutoff,
            )
            torrent_result = await session.execute(torrent_stmt)
            torrent_count = torrent_result.scalar_one()

            return {
                "searches": search_count,
                "torrents_created": torrent_count,
            }


# Global service instance
db_service = DatabaseService()


async def get_db_service() -> DatabaseService:
    """Get the database service instance."""
    if not db_service._initialized:
        await db_service.initialize()
    return db_service