import asyncio
from unittest.mock import AsyncMock, MagicMock, Mock, patch
from fastapi import FastAPI
import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from redis.asyncio import Redis
from sqlalchemy.pool import StaticPool
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from main import app, lifespan
from app.models.models import Base, Contact, User
from app.database.db import get_db
from app.database.redis import get_redis
from app.services.auth import Auth, auth_service

SQLALCHEMY_DATABASE_URL = "sqlite+aiosqlite:///./test.db"

engine = create_async_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)

TestingSessionLocal = async_sessionmaker(
    autocommit=False, autoflush=False, expire_on_commit=False, bind=engine
)

test_admin_user = {
    "username": "username1",
    "email": "email1@example.com",
    "password": "password1",
}
test__not_admin_user = {
    "username": "username2",
    "email": "email2@example.com",
    "password": "password2",
}
hash_test_admin_user = auth_service.get_password_hash(test_admin_user["password"])
hash_test__not_admin_user = auth_service.get_password_hash(
    test__not_admin_user["password"]
)
admin = User(
    username=test_admin_user["username"],
    email=test_admin_user["email"],
    password=hash_test_admin_user,
    verified=True,
    role="admin",
)
user = User(
    username=test__not_admin_user["username"],
    email=test__not_admin_user["email"],
    password=hash_test__not_admin_user,
    verified=True,
    role="user",
)


@pytest.fixture(scope="session", autouse=True)
def init_models_wrap():
    async def init_models():
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
            await conn.run_sync(Base.metadata.create_all)
        async with TestingSessionLocal() as session:
            session.add(admin)
            session.add(user)
            await session.commit()

    asyncio.run(init_models())


@pytest.fixture(scope="module")
def client():
    # Dependency override
    async def override_get_db():
        session = TestingSessionLocal()
        try:
            yield session
        except Exception as err:
            await session.rollback()
            raise
        finally:
            await session.close()

    async def override_get_redis():
        mock_redis = AsyncMock(spec=Redis)
        mock_redis.get = AsyncMock(return_value=None)
        mock_redis.set = AsyncMock(return_value=True)
        mock_redis.expire = AsyncMock(return_value=True)

        return mock_redis

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_redis] = override_get_redis

    yield TestClient(app)

    app.dependency_overrides.clear()


@pytest.fixture(scope="function")
def mock_auth_settings():
    with patch.object(Auth, "SECRET_KEY", "mocked_secret_key"), patch.object(
        Auth, "ALGORITHM", "HS256"
    ), patch.object(Auth, "ACCESS_TOKEN_EXPIRE_MINUTES", 15):
        yield


@pytest_asyncio.fixture(scope="function")
async def get_token_admin(mock_auth_settings):
    token = await auth_service.create_access_token(
        data={"sub": test_admin_user["email"]}
    )
    return token


@pytest_asyncio.fixture(scope="function")
async def get_token_not_admin(mock_auth_settings):
    token = await auth_service.create_access_token(
        data={"sub": test__not_admin_user["email"]}
    )
    return token


@pytest_asyncio.fixture(scope="function")
@patch.object(Auth, "SECRET_KEY", "mocked_secret_key")
@patch.object(Auth, "ALGORITHM", "HS256")
@patch.object(Auth, "REFRESH_TOKEN_EXPIRE_DAYS", 15)
async def get_refresh_admin():
    token = await auth_service.create_refresh_token(
        data={"sub": test_admin_user["email"]}
    )
    return token


class TestFixtures:
    @pytest.fixture(autouse=True, scope="function")
    def setup_db(self):
        mock_db: AsyncSession = AsyncMock(spec=AsyncSession)
        mock_db.execute = AsyncMock()
        mock_db.add = AsyncMock()
        mock_db.commit = AsyncMock()
        mock_db.refresh = AsyncMock()
        return mock_db

    @pytest.fixture(scope="function")
    def setup_user(self):
        mock_user = Mock(spec=User)
        mock_user.id = 1
        mock_user.username = "username"
        mock_user.email = "email@example.com"
        mock_user.password = "password"
        mock_user.role = "admin"
        mock_user.verified = False
        mock_user.avatar = None
        return mock_user

    @pytest.fixture(scope="function")
    def setup_contacts(self):
        mock_contact1 = MagicMock(spec=Contact)
        mock_contact1.id = 1
        mock_contact1.name = "John"
        mock_contact1.surname = "Doe"
        mock_contact1.email = "john.doe@example.com"
        mock_contact1.phone = "+380968345768"
        mock_contact1.date_of_birth = "1990-05-20"
        mock_contact1.additional_info = "Friend from work"
        mock_contact1.user_id = 1

        mock_contact2 = MagicMock(spec=Contact)
        mock_contact2.id = 2
        mock_contact2.name = "Jane"
        mock_contact2.surname = "Smith"
        mock_contact2.email = "jane.smith@example.com"
        mock_contact2.phone = "+380938475667"
        mock_contact2.date_of_birth = "1985-08-15"
        mock_contact2.additional_info = "Gym trainer"
        mock_contact2.user_id = 1

        mock_contact3 = MagicMock(spec=Contact)
        mock_contact3.id = 3
        mock_contact3.name = "Mark"
        mock_contact3.surname = "Smith"
        mock_contact3.email = "mark.smith@example.com"
        mock_contact3.phone = "+380938454567"
        mock_contact3.date_of_birth = "1999-12-24"
        mock_contact3.additional_info = "worker"
        mock_contact3.user_id = 1
        return [mock_contact1, mock_contact2, mock_contact3]

    @pytest.fixture(scope="function")
    def setup_dict_contacts(self):
        return {
                "id": 1,
                "name": "John",
                "surname": "Doe",
                "email": "john.doe@example.com",
                "phone": "+380968345768",
                "date_of_birth": "1990-05-20",
                "additional_info": "Friend from work",
                "completed":True
            }

