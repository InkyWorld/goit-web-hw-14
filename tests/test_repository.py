import pytest
from unittest.mock import AsyncMock, Mock
from app.repository.users import confirmed_email, create_user, get_user_by_email, update_avatar_url, update_token
from app.models.models import User
from sqlalchemy.ext.asyncio import AsyncSession
from app.schemas.user import UserCreationSchema

@pytest.mark.asyncio
class TestGetUserByEmail():

    @pytest.fixture(autouse=True)
    def setup(self):
        self.mock_db = AsyncMock(spec=AsyncSession)
        self.mock_user = Mock(spec=User)
        self.mock_user.id = 1
        self.mock_user.username = "username"
        self.mock_user.email = "email@example.com"
        self.mock_user.password = "password"
        self.mock_user.role = "admin"
        self.mock_user.verified = False
        self.mock_user.avatar = None

    async def test_get_user_by_email_existing(self):
        email = "email@example.com"
        mock_result = AsyncMock()
        self.mock_db.execute.return_value = mock_result
        mock_result.scalar_one_or_none.return_value = self.mock_user

        user = await get_user_by_email(email=email, db=self.mock_db)
        assert await user == self.mock_user
        self.mock_db.execute.assert_called_once()
    
    async def test_get_user_by_email_not_found(self):
        email = "invalid_email@example.com"
        self.mock_db.execute.return_value.scalar_one_or_none.return_value = None
        user = await get_user_by_email(email=email, db=self.mock_db)
        assert await user == None
        self.mock_db.execute.assert_called_once()

    async def test_create_user(self):
        body = UserCreationSchema(username="username", email="email@example.com", password="password")
        self.mock_db.commit = AsyncMock()
        self.mock_db.refresh = AsyncMock()
        created_user = await create_user(body=body, db=self.mock_db)

        assert created_user.username == "username"
        assert created_user.email == "email@example.com"
        
        self.mock_db.add.assert_called_once_with(created_user)
        self.mock_db.commit.assert_called_once()
        self.mock_db.refresh.assert_called_once_with(created_user)

    async def test_update_token(self):
        new_token = "new_refresh_token_value"
        await update_token(self.mock_user, new_token, self.mock_db)
        assert self.mock_user.refresh_token == new_token
        self.mock_db.commit.assert_called_once()

    async def test_confirmed_email(self):
        get_user_by_email_mock = AsyncMock(return_value=self.mock_user)
        # No need to reassign get_user_by_email to the mock
        await confirmed_email("email@example.com", self.mock_db)
        assert self.mock_user.verified is True
        self.mock_db.commit.assert_called_once()

    async def test_confirmed_email_user_not_found(self):
        email = "nonexistinguser@example.com"
        get_user_by_email_mock = AsyncMock(return_value=None)

        with pytest.raises(Exception):
            await confirmed_email(email, self.mock_db)
        
        self.mock_db.commit.assert_not_called()

    async def test_update_avatar_url(self):
        new_url = "https://example.com/image_example"
        self.mock_user.avatar = "old_url"
        self.mock_db.commit = AsyncMock()
        self.mock_db.refresh = AsyncMock()
        get_user_by_email_mock = AsyncMock(return_value=self.mock_user)
        user = await update_avatar_url("email@example.com", new_url, self.mock_db)
        assert user.avatar == new_url
        self.mock_db.commit.assert_called_once()
        get_user_by_email_mock.assert_called_once_with("email@example.com", self.mock_db)
