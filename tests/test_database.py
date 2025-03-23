import pytest
from unittest.mock import AsyncMock, MagicMock, Mock, patch

from app.database.db import get_db


@pytest.fixture
def mock_session_maker():
    """Fixture for mocking session_maker."""
    return AsyncMock(return_value=AsyncMock())


@pytest.mark.asyncio
class TestDB:
    @patch("app.conf.config.db_config.DATABASE_URL")
    async def test_session_initialization_with_mocked_session_maker(self, mock_db_url):
        from app.database.db import DatabaseSessionManager

        mock_session = AsyncMock()
        mock_session.rollback = AsyncMock()
        mock_session.close = AsyncMock()

        mock_db_url.return_value = "sqlite+aiosqlite:///./test.db"
        sessionmaker = MagicMock()
        sessionmaker.return_value = mock_session

        sessionmanager = DatabaseSessionManager(mock_db_url.return_value)
        sessionmanager._session_maker = sessionmaker

        async with sessionmanager.session() as s:
            assert s == mock_session
            sessionmaker.assert_called_once()
            mock_session.rollback.assert_not_called()
            mock_session.close.assert_not_called()
        mock_session.close.assert_called_once()

    @patch("app.conf.config.db_config.DATABASE_URL")
    async def test_session_not_initialized(self, mock_db_url):
        from app.database.db import DatabaseSessionManager

        mock_db_url.return_value = "sqlite+aiosqlite:///./test.db"

        sessionmanager = DatabaseSessionManager(mock_db_url.return_value)
        sessionmanager._session_maker = None

        with pytest.raises(Exception, match="Session is not initialized"):
            async with sessionmanager.session():
                pass

    @patch("app.conf.config.db_config.DATABASE_URL")
    async def test_session_initialization_with_mocked_session_maker(self, mock_db_url):
        from app.database.db import DatabaseSessionManager

        mock_session = AsyncMock()
        mock_session.rollback = AsyncMock()
        mock_session.close = AsyncMock()

        mock_db_url.return_value = "sqlite+aiosqlite:///./test.db"
        sessionmaker = MagicMock()
        sessionmaker.return_value = mock_session

        sessionmanager = DatabaseSessionManager(mock_db_url.return_value)
        sessionmanager._session_maker = sessionmaker

        with pytest.raises(Exception):
            async with sessionmanager.session():
                raise Exception("Test exception")
        mock_session.rollback.assert_called_once()
        mock_session.close.assert_called_once()

    @patch("app.conf.config.db_config.DATABASE_URL")
    async def test_get_db(self, mock_db_url):
        from app.database.db import sessionmanager

        mock_session = AsyncMock()
        mock_session.__aenter__.return_value = mock_session
        mock_session.__aexit__.return_value = None
        sessionmanager.session = Mock(return_value=mock_session)

        async for session in get_db():
            assert session == mock_session
