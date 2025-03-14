import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from unittest.mock import AsyncMock, patch

from app.models.models import User
from app.repository.users import get_user_by_email


@pytest.mark.asyncio

@pytest.mark.asyncio
async def test_get_user_by_email():
    # Arrange
    email = "test@example.com"
    mock_db = AsyncMock()
    mock_user = User(email=email, username="testuser")
    mock_result = AsyncMock()
    mock_result.scalar_one_or_none.return_value = mock_user
    mock_db.execute.return_value = mock_result

    # Act
    result = await get_user_by_email(email, db=mock_db)

    # Assert
    assert result == mock_user
    mock_db.execute.assert_called_once()
    mock_result.scalar_one_or_none.assert_called_once()
