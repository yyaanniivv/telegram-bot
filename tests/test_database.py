"""Tests for database models and service."""
import os
import tempfile
import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from datetime import datetime, timedelta

import pytest_asyncio

from database import (
    Base,
    ApprovedUser,
    SearchHistory,
    CreatedTorrent,
    AnalyticsEvent,
    DatabaseManager,
    get_database_url,
    get_sync_database_url,
    init_database,
    get_db_session,
)
from db_service import DatabaseService


class TestDatabaseModels:
    """Tests for database models."""

    @pytest.fixture
    def temp_db_url(self):
        """Create a temporary database URL for testing."""
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
            db_path = f.name
        yield f"sqlite+aiosqlite:///{db_path}"
        # Cleanup
        try:
            os.unlink(db_path)
        except:
            pass

    @pytest_asyncio.fixture
    async def db_manager(self, temp_db_url):
        """Create a database manager with a temporary database."""
        manager = DatabaseManager(temp_db_url)
        manager.init_async_engine()
        await manager.create_tables()
        yield manager
        await manager.close()

    @pytest_asyncio.fixture
    async def db_session(self, db_manager):
        """Get a database session for testing."""
        session = db_manager.get_session()
        yield session
        await session.close()

    @pytest.mark.asyncio
    async def test_approved_user_creation(self, db_session):
        """Test creating an approved user."""
        user = ApprovedUser(id=12345, username="testuser", is_active=True)
        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)

        assert user.id == 12345
        assert user.username == "testuser"
        assert user.is_active is True
        assert user.created_at is not None

    @pytest.mark.asyncio
    async def test_search_history_creation(self, db_session):
        """Test creating a search history record."""
        # First create a user
        user = ApprovedUser(id=12345, username="testuser", is_active=True)
        db_session.add(user)
        await db_session.commit()

        # Create search history
        search = SearchHistory(user_id=12345, query="test query", results_count=5)
        db_session.add(search)
        await db_session.commit()
        await db_session.refresh(search)

        assert search.id is not None
        assert search.user_id == 12345
        assert search.query == "test query"
        assert search.results_count == 5
        assert search.created_at is not None

    @pytest.mark.asyncio
    async def test_created_torrent_creation(self, db_session):
        """Test creating a torrent record."""
        # First create a user
        user = ApprovedUser(id=12345, username="testuser", is_active=True)
        db_session.add(user)
        await db_session.commit()

        # Create torrent record
        torrent = CreatedTorrent(
            user_id=12345,
            btih="abcd1234efab5678efab9012abcd3456efab7890",
            magnet_link="magnet:?xt=urn:btih:abcd1234efab5678efab9012abcd3456efab7890",
            search_term="test search",
            filename="bot-12345-test.torrent",
            file_path="/output/bot-12345-test.torrent",
            file_size_bytes=1024,
        )
        db_session.add(torrent)
        await db_session.commit()
        await db_session.refresh(torrent)

        assert torrent.id is not None
        assert torrent.btih == "abcd1234efab5678efab9012abcd3456efab7890"
        assert torrent.search_term == "test search"
        assert torrent.file_size_bytes == 1024

    @pytest.mark.asyncio
    async def test_analytics_event_creation(self, db_session):
        """Test creating an analytics event."""
        event = AnalyticsEvent(
            user_id=12345,
            event_type="inline_search",
            event_data='{"query": "test", "results": 5}',
        )
        db_session.add(event)
        await db_session.commit()
        await db_session.refresh(event)

        assert event.id is not None
        assert event.event_type == "inline_search"
        assert event.event_data == '{"query": "test", "results": 5}'


class TestDatabaseService:
    """Tests for DatabaseService."""

    @pytest.fixture
    def temp_db_url(self):
        """Create a temporary database URL for testing."""
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
            db_path = f.name
        yield f"sqlite+aiosqlite:///{db_path}"
        # Cleanup
        try:
            os.unlink(db_path)
        except:
            pass

    @pytest_asyncio.fixture
    async def db_service(self, temp_db_url):
        """Create a database service with a temporary database."""
        # Patch the global database manager in database module
        import database
        original_db_manager = database.db_manager

        mock_manager = DatabaseManager(temp_db_url)
        mock_manager.init_async_engine()
        await mock_manager.create_tables()
        database.db_manager = mock_manager

        service = DatabaseService()
        service._initialized = True
        yield service
        await mock_manager.close()
        database.db_manager = original_db_manager

    @pytest.mark.asyncio
    async def test_record_search(self, db_service):
        """Test recording a search."""
        search = await db_service.record_search(12345, "test query", 10)
        assert search.user_id == 12345
        assert search.query == "test query"
        assert search.results_count == 10

    @pytest.mark.asyncio
    async def test_get_user_search_history(self, db_service):
        """Test getting user search history."""
        # Record some searches
        await db_service.record_search(12345, "query 1", 5)
        await db_service.record_search(12345, "query 2", 3)
        await db_service.record_search(99999, "other user query", 1)

        history = await db_service.get_user_search_history(12345, limit=10)
        assert len(history) == 2
        # Should be ordered by created_at desc
        assert history[0].query == "query 2"
        assert history[1].query == "query 1"

    @pytest.mark.asyncio
    async def test_record_created_torrent(self, db_service):
        """Test recording a created torrent."""
        torrent = await db_service.record_created_torrent(
            user_id=12345,
            btih="abcd1234efab5678efab9012abcd3456efab7890",
            magnet_link="magnet:?xt=urn:btih:abcd1234efab5678efab9012abcd3456efab7890",
            search_term="test search",
            filename="bot-12345-test.torrent",
            file_path="/output/bot-12345-test.torrent",
            file_size_bytes=2048,
        )
        assert torrent.btih == "abcd1234efab5678efab9012abcd3456efab7890"
        assert torrent.file_size_bytes == 2048

    @pytest.mark.asyncio
    async def test_get_user_torrents(self, db_service):
        """Test getting user torrents."""
        btih1 = "aaaa1234efab5678efab9012abcd3456efab7890"
        btih2 = "bbbb1234efab5678efab9012abcd3456efab7890"

        await db_service.record_created_torrent(
            12345, btih1, f"magnet:?xt=urn:btih:{btih1}", "search 1",
            "file1.torrent", "/output/file1.torrent"
        )
        await db_service.record_created_torrent(
            12345, btih2, f"magnet:?xt=urn:btih:{btih2}", "search 2",
            "file2.torrent", "/output/file2.torrent"
        )
        await db_service.record_created_torrent(
            99999, "cccc1234efab5678efab9012abcd3456efab7890",
            "magnet:?xt=urn:btih:cccc1234efab5678efab9012abcd3456efab7890",
            "other", "file3.torrent", "/output/file3.torrent"
        )

        torrents = await db_service.get_user_torrents(12345, limit=10)
        assert len(torrents) == 2
        # Should be ordered by created_at desc
        assert torrents[0].btih == btih2
        assert torrents[1].btih == btih1

    @pytest.mark.asyncio
    async def test_record_event(self, db_service):
        """Test recording an analytics event."""
        event = await db_service.record_event("test_event", 12345, {"key": "value"})
        assert event.event_type == "test_event"
        assert event.user_id == 12345
        assert event.event_data == '{"key": "value"}'

    @pytest.mark.asyncio
    async def test_get_event_counts(self, db_service):
        """Test getting event counts."""
        await db_service.record_event("event_a", 12345)
        await db_service.record_event("event_a", 12345)
        await db_service.record_event("event_b", 12345)
        await db_service.record_event("event_a", 99999)

        counts = await db_service.get_event_counts(days=7)
        assert counts["event_a"] == 3
        assert counts["event_b"] == 1

    @pytest.mark.asyncio
    async def test_get_user_activity(self, db_service):
        """Test getting user activity summary."""
        await db_service.record_search(12345, "query 1", 5)
        await db_service.record_search(12345, "query 2", 3)
        await db_service.record_created_torrent(
            12345, "abcd1234efab5678efab9012abcd3456efab7890",
            "magnet:?xt=urn:btih:abcd1234efab5678efab9012abcd3456efab7890",
            "search", "file.torrent", "/output/file.torrent"
        )

        activity = await db_service.get_user_activity(12345, days=30)
        assert activity["searches"] == 2
        assert activity["torrents_created"] == 1

    @pytest.mark.asyncio
    async def test_get_popular_searches(self, db_service):
        """Test getting popular searches."""
        await db_service.record_search(12345, "popular query", 5)
        await db_service.record_search(12345, "popular query", 3)
        await db_service.record_search(99999, "popular query", 1)
        await db_service.record_search(12345, "less popular", 2)

        popular = await db_service.get_popular_searches(limit=5)
        assert len(popular) >= 1
        assert popular[0]["query"] == "popular query"
        assert popular[0]["count"] == 3


if __name__ == "__main__":
    pytest.main([__file__, "-v"])