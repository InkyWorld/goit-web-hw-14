from datetime import datetime, timedelta, timezone
import pickle
from unittest.mock import AsyncMock, MagicMock, Mock, patch
from fastapi import HTTPException, UploadFile, status
import pytest
from jose import JWTError, jwt

from app.models.models import Role, User
from app.services.cloudinary import claudinary as cloud_service
from app.services.email import send_email
from app.services.roles import RoleAccess
from tests.conftest import TestFixtures
from app.services.auth import Auth, auth_service


@pytest.mark.asyncio
class TestRoles:
    async def test_role_access_granted(self):
        role_access = RoleAccess([Role.admin, Role.moderator])
        user = User(role=Role.admin)
        request = MagicMock()

        await role_access(request, user)
        assert True

    async def test_role_access_denied(self):
        role_access = RoleAccess([Role.admin, Role.moderator])
        user = User(role=Role.user)
        request = MagicMock()

        with pytest.raises(HTTPException) as exc_info:
            await role_access(request, user)

        assert exc_info.value.status_code == status.HTTP_403_FORBIDDEN
        assert exc_info.value.detail == "FORBIDDEN"


@pytest.mark.asyncio
class TestEmail:
    @patch(
        "app.services.auth.auth_service.create_email_token", return_value="mocked-token"
    )
    @patch("app.services.email.FastMail")
    @patch("app.services.email.conf")
    async def test_send_email_success(
        self, mock_conf, MockFastMail, mock_create_email_token
    ):
        username = "john_doe"
        email = "example@example.com"
        host = "https://example.com"

        fm = AsyncMock()
        fm.send_message.return_value = None
        MockFastMail.return_value = fm
        await send_email(email=email, username=username, host=host)

        # Assertions
        fm.send_message.assert_called_once()
        MockFastMail.assert_called_once()

    @patch(
        "app.services.auth.auth_service.create_email_token", return_value="mocked-token"
    )
    @patch("app.services.email.FastMail")
    @patch("app.services.email.conf")
    async def test_send_email_connection_error(
        self, mock_conf, MockFastMail, mock_create_email_token
    ):
        fm = AsyncMock()
        fm.send_message.side_effect = ConnectionError("Failed to connect to the server")
        MockFastMail.return_value = fm

        with pytest.raises(ConnectionError):
            await send_email(
                email="example@example.com",
                username="john_doe",
                host="https://example.com",
            )

        fm.send_message.assert_called_once()


@pytest.mark.asyncio
class TestCloudinary:
    @patch("app.services.cloudinary.upload")
    async def test_upload_avatar_to_cloudinary_public_id_missing(self, mock_upload):
        # Setup mock return values
        mock_upload.return_value = {"version": "123"}

        # Create a mock file
        mock_file = Mock(spec=UploadFile)
        mock_file.file = Mock()

        # Call the function
        with pytest.raises(HTTPException) as exc_info:
            await cloud_service.upload_avatar_to_cloudinary(
                file=mock_file, user_email="example@example.com"
            )
        assert (
            exc_info.value.detail
            == "Failed to upload to Cloudinary: 500: Failed to retrieve public_id from Cloudinary"
        )

    @patch("app.services.cloudinary.upload")
    @patch("app.services.cloudinary.cloudinary_url")
    async def test_upload_avatar_to_cloudinary_exception(
        self, mock_cloudinary_url, mock_upload
    ):
        # Setup mock return values
        mock_upload.return_value = {"public_id": "sample_public_id", "version": "123"}
        mock_cloudinary_url.return_value = ("https://example.com/image_example", {})
        mock_upload.side_effect = Exception("Upload failed")
        # Create a mock file
        mock_file = Mock(spec=UploadFile)
        mock_file.file = Mock()

        # Call the function
        with pytest.raises(HTTPException) as exc_info:
            await cloud_service.upload_avatar_to_cloudinary(
                file=mock_file, user_email="example@example.com"
            )

        # Assertions
        assert exc_info.value.status_code == 500
        assert "Failed to upload to Cloudinary: Upload failed" == exc_info.value.detail

    @patch("app.services.cloudinary.upload")
    @patch("app.services.cloudinary.cloudinary_url")
    async def test_upload_avatar_to_cloudinary(self, mock_cloudinary_url, mock_upload):
        # Setup mock return values
        mock_upload.return_value = {"public_id": "sample_public_id", "version": "123"}
        mock_cloudinary_url.return_value = ("https://example.com/image_example", {})

        # Create a mock file
        mock_file = Mock(spec=UploadFile)
        mock_file.file = Mock()

        # Call the function
        result_url = await cloud_service.upload_avatar_to_cloudinary(
            file=mock_file, user_email="example@example.com"
        )

        # Assertions
        mock_upload.assert_called_once_with(
            mock_file.file, folder="web13/example@example.com", overwrite=True
        )
        mock_cloudinary_url.assert_called_once_with(
            "sample_public_id", width=250, height=250, crop="fit", version="123"
        )
        assert result_url == "https://example.com/image_example"


class TestAuthSync:
    @patch("app.services.auth.Auth.pwd_context")
    def test_verify_password_success(self, mock_pwd_context):
        mock_pwd_context.verify.return_value = True
        result = auth_service.verify_password("password", "password")
        mock_pwd_context.verify.assert_called_once_with("password", "password")
        assert result is True

    @patch("app.services.auth.Auth.pwd_context")
    def test_verify_password_fail(self, mock_pwd_context):
        mock_pwd_context.verify.return_value = False
        result = auth_service.verify_password("password", "123")
        mock_pwd_context.verify.assert_called_once_with("password", "123")
        assert result is False

    @patch("app.services.auth.Auth.pwd_context")
    def test_get_password_hash(self, mock_pwd_context):
        mock_pwd_context.hash.return_value = "mock_hash_password"
        result = auth_service.get_password_hash("password")
        mock_pwd_context.hash.assert_called_once_with("password")
        assert result == "mock_hash_password"


@pytest.mark.asyncio
class TestAuthAsync(TestFixtures):
    auth_service = Auth()
    auth_service.ACCESS_TOKEN_EXPIRE_MINUTES = 15
    auth_service.SECRET_KEY = "secret"
    auth_service.ALGORITHM = "HS256"
    auth_service.REFRESH_TOKEN_EXPIRE_DAYS = 7

    async def test_create_access_token_with_default_expiration(self):
        data = {"sub": "user123"}
        token = await auth_service.create_access_token(data)

        # Decode the token to check its contents
        decoded_token = jwt.decode(
            token,
            auth_service.SECRET_KEY,
            algorithms=[auth_service.ALGORITHM],
        )

        # Assertions
        assert decoded_token["sub"] == "user123"
        assert "iat" in decoded_token
        assert "exp" in decoded_token

        now = datetime.now(timezone.utc)
        expected_expiration = now + timedelta(
            minutes=auth_service.ACCESS_TOKEN_EXPIRE_MINUTES
        )
        assert abs(decoded_token["exp"] - expected_expiration.timestamp()) < 60
        assert decoded_token["scope"] == "access_token"

    async def test_create_access_token_with_custom_expiration(self):
        data = {"sub": "user123"}
        expires_delta = timedelta(minutes=30)

        token = await auth_service.create_access_token(data, expires_delta)

        decoded_token = jwt.decode(
            token,
            auth_service.SECRET_KEY,
            algorithms=[auth_service.ALGORITHM],
        )

        now = datetime.now(timezone.utc)
        expected_expiration = now + expires_delta
        assert abs(decoded_token["exp"] - expected_expiration.timestamp()) < 60
        assert decoded_token["scope"] == "access_token"

    async def test_create_refresh_token_with_default_expiration(self):
        data = {"sub": "user123"}
        token = await auth_service.create_refresh_token(data)

        # Decode the token to check its contents
        decoded_token = jwt.decode(
            token,
            auth_service.SECRET_KEY,
            algorithms=[auth_service.ALGORITHM],
        )

        # Assertions
        assert decoded_token["sub"] == "user123"
        assert "iat" in decoded_token
        assert "exp" in decoded_token

        now = datetime.now(timezone.utc)
        expected_expiration = now + timedelta(
            days=auth_service.REFRESH_TOKEN_EXPIRE_DAYS
        )
        assert abs(decoded_token["exp"] - expected_expiration.timestamp()) < 60
        assert decoded_token["scope"] == "refresh_token"

    async def test_create_refresh_token_with_custom_expiration(self):
        data = {"sub": "user123"}
        expires_delta = timedelta(minutes=30)

        token = await auth_service.create_refresh_token(data, expires_delta)

        decoded_token = jwt.decode(
            token,
            auth_service.SECRET_KEY,
            algorithms=[auth_service.ALGORITHM],
        )

        now = datetime.now(timezone.utc)
        expected_expiration = now + expires_delta
        assert abs(decoded_token["exp"] - expected_expiration.timestamp()) < 60
        assert decoded_token["scope"] == "refresh_token"

    async def test_decode_refresh_token(self):
        iat = datetime.now(timezone.utc)
        exp = datetime.now(timezone.utc) + timedelta(minutes=15)
        payload = {
            "sub": "user@example.com",
            "scope": "refresh_token",
            "iat": iat,
            "exp": exp,
        }
        refresh_token = jwt.encode(
            payload, auth_service.SECRET_KEY, algorithm=auth_service.ALGORITHM
        )

        email = await auth_service.decode_refresh_token(refresh_token)

        assert email == "user@example.com"
        assert payload["sub"] == email
        assert payload["iat"] == int(iat.timestamp())
        assert payload["exp"] == int(exp.timestamp())
        assert payload["scope"] == "refresh_token"

    async def test_decode_refresh_token_invalid_scope(self):
        auth_service = Auth()
        auth_service.SECRET_KEY = "secret"
        auth_service.ALGORITHM = "HS256"

        payload = {
            "sub": "user@example.com",
            "scope": "access_token",
            "iat": datetime.now(timezone.utc),
            "exp": datetime.now(timezone.utc) + timedelta(minutes=15),
        }
        refresh_token = jwt.encode(
            payload, auth_service.SECRET_KEY, algorithm=auth_service.ALGORITHM
        )

        with pytest.raises(HTTPException) as excinfo:
            await auth_service.decode_refresh_token(refresh_token)

        assert excinfo.value.status_code == 401
        assert excinfo.value.detail == "Invalid scope for token"

    async def test_decode_refresh_token_invalid_token(self):
        invalid_token = "invalid.token.value"
        with pytest.raises(HTTPException) as excinfo:
            await auth_service.decode_refresh_token(invalid_token)

        assert excinfo.value.status_code == 401
        assert excinfo.value.detail == "Could not validate credential"

    @patch(
        "app.services.auth.jwt.decode",
        return_value={"sub": "test@example.com", "scope": "access_token"},
    )
    async def test_authenticate_user_success(mock_jwt_decode, setup_db):

        redis_mock = AsyncMock()
        redis_mock.get.return_value = None  # Simulating a cache miss

        test_user = User(
            id=1,
            username="username",
            email="email@example.com",
            password="password",
            role="admin",
            verified=False,
            avatar=None,
        )
        with patch(
            "app.repository.users.get_user_by_email", AsyncMock(return_value=test_user)
        ) as mock_get_user:

            # Call the function
            user = await auth_service.authenticate_user(
                token="valid_token", db=setup_db, redis=redis_mock
            )

            # Assertions
            assert user == test_user
            redis_mock.get.assert_called_once_with("user:test@example.com")
            mock_get_user.assert_called_once_with("test@example.com", setup_db)
            redis_mock.set.assert_called_once_with(
                "user:test@example.com", pickle.dumps(test_user)
            )
            redis_mock.expire.assert_called_once_with("user:test@example.com", 900)

    @patch("app.services.auth.jwt.decode")
    async def test_authenticate_user_invalid_token(mock_jwt_decode, setup_db):
        mock_jwt_decode.side_effect = JWTError("Invalid token")

        # Mock dependencies
        redis_mock = AsyncMock()

        with pytest.raises(HTTPException) as exc_info:
            await auth_service.authenticate_user(
                token="invalid_token", db=setup_db, redis=redis_mock
            )

        # Assertions
        assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
        assert exc_info.value.detail == "Could not validate credentials"
        assert exc_info.value.headers == {"WWW-Authenticate": "Bearer"}

    @patch("app.services.auth.jwt.decode")
    async def test_authenticate_user_user_not_found(self, mock_jwt_decode, setup_db):
        mock_jwt_decode.return_value = {
            "sub": "unknown@example.com",
            "scope": "access_token",
        }
        redis_mock = AsyncMock()
        redis_mock.get.return_value = None

        with patch(
            "app.repository.users.get_user_by_email", AsyncMock(return_value=None)
        ):
            with pytest.raises(HTTPException) as exc_info:
                await auth_service.authenticate_user(
                    token="valid_token", db=setup_db, redis=redis_mock
                )

        # Assertions
        assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
        assert exc_info.value.detail == "Could not validate credentials"

    async def test_create_email_token(self):
        data = {"sub": "user123"}
        token = await auth_service.create_refresh_token(data)
        decoded_token = jwt.decode(
            token,
            auth_service.SECRET_KEY,
            algorithms=[auth_service.ALGORITHM],
        )
        assert "iat" in decoded_token
        assert "exp" in decoded_token
        assert decoded_token["sub"] == "user123"

    async def test_verify_email_token_valid(self):
        email = "user@example.com"
        payload = {
            "sub": email,
            "exp": datetime.now(timezone.utc) + timedelta(minutes=30),
        }
        valid_token = jwt.encode(
            payload, auth_service.SECRET_KEY, algorithm=auth_service.ALGORITHM
        )

        result = await auth_service.verify_email_token(valid_token)
        assert result == email

    async def test_verify_email_token_invalid(self):
        invalid_token = "invalid.token.value"
        with pytest.raises(HTTPException) as excinfo:
            await auth_service.verify_email_token(invalid_token)

        assert excinfo.value.status_code == status.HTTP_403_FORBIDDEN
        assert excinfo.value.detail == "Invalid email verification token"

    async def test_verify_email_token_expired(self):
        email = "user@example.com"
        payload = {"sub": email, "exp": datetime.now(timezone.utc) - timedelta(minutes=1)}
        expired_token = jwt.encode(
            payload, auth_service.SECRET_KEY, algorithm=auth_service.ALGORITHM
        )

        with pytest.raises(HTTPException) as excinfo:
            await auth_service.verify_email_token(expired_token)

        assert excinfo.value.status_code == status.HTTP_403_FORBIDDEN
        assert excinfo.value.detail == "Invalid email verification token"
