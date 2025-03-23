import io
import json
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, MagicMock, patch

from fastapi.testclient import TestClient
from fastapi import status
import pytest
from app.models.models import User
from sqlalchemy.ext.asyncio import AsyncSession
from app.schemas.user import UserCreationSchema
from conftest import test_admin_user, TestFixtures

user_data = {
    "email": "test@example.com",
    "username": "testuser",
    "password": "Khfj98945bUGe",
}


@pytest.mark.asyncio
class TestAuth:
    @patch("app.routes.auth.BackgroundTasks.add_task", new_callable=Mock)
    @patch("app.repository.users.create_user", new_callable=AsyncMock)
    @patch("app.services.auth.Auth.get_password_hash", new_callable=Mock)
    @patch("app.repository.users.get_user_by_email", new_callable=AsyncMock)
    async def test_signup(
        self,
        mock_get_user_by_email,
        mock_get_password_hash,
        mock_create_user,
        bt,
        client: TestClient,
    ):
        mock_get_user_by_email.return_value = None
        mock_get_password_hash.return_value = "hashed_password"
        mock_create_user.return_value = SimpleNamespace(
            **{"username": "mock_username", "email": "mock@email.com"}
        )
        response = client.post("/api/auth/signup", json=user_data)
        assert response.status_code == status.HTTP_201_CREATED
        assert response.json()["username"] == "mock_username"

    @patch("app.repository.users.get_user_by_email", new_callable=AsyncMock)
    async def test_signup_exist_user(self, mock_get_user_by_email, client: TestClient):
        mock_get_user_by_email.return_value = Mock(email=user_data["email"])
        response = client.post("/api/auth/signup", json=user_data)
        assert response.status_code == status.HTTP_409_CONFLICT
        assert response.json()["detail"] == "Account already exists"

    @patch("app.services.auth.Auth.create_access_token", new_callable=AsyncMock)
    @patch("app.services.auth.Auth.create_refresh_token", new_callable=AsyncMock)
    @patch("app.repository.users.update_token", new_callable=AsyncMock)
    @patch("app.repository.users.get_user_by_email", new_callable=AsyncMock)
    @patch("app.services.auth.Auth.verify_password", new_callable=Mock)
    async def test_login_successful(
        self,
        mock_verify_password,
        mock_get_user_by_email,
        mock_update,
        mock_refresh,
        mock_access,
        client: TestClient,
    ):
        mock_get_user_by_email.return_value = Mock(
            email=test_admin_user["email"], verified=True
        )
        mock_refresh.return_value = "new_refresh_token"
        mock_access.return_value = "access_token"
        mock_update.return_value = Mock()
        mock_verify_password.return_value = True
        response = client.post(
            "/api/auth/login",
            data={
                "username": "email1@example.com",
                "password": "password1",
            },
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["access_token"]

    @patch("app.repository.users.get_user_by_email", new_callable=AsyncMock)
    async def test_login_invalid_email(
        self, mock_get_user_by_email, client: TestClient
    ):
        mock_get_user_by_email.return_value = None
        response = client.post(
            "/api/auth/login",
            data={
                "username": "wrong_email@example.com",
                "password": test_admin_user["password"],
            },
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert response.json() == {"detail": "Invalid email"}

    @patch("app.repository.users.get_user_by_email", new_callable=AsyncMock)
    async def test_login_email_not_verified(
        self, mock_get_user_by_email, client: TestClient
    ):
        mock_get_user_by_email.return_value = Mock(
            email=test_admin_user["email"], verified=False
        )
        response = client.post(
            "/api/auth/login",
            data={
                "username": test_admin_user["email"],
                "password": test_admin_user["password"],
            },
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert response.json() == {"detail": "Email not verified"}

    @patch("app.repository.users.get_user_by_email", new_callable=AsyncMock)
    @patch("app.services.auth.Auth.verify_password", new_callable=Mock)
    async def test_login_invalid_password(
        self, mock_verify_password, mock_get_user_by_email, client: TestClient
    ):
        mock_get_user_by_email.return_value = Mock(
            email=test_admin_user["email"], verified=True
        )
        mock_verify_password.return_value = False
        response = client.post(
            "/api/auth/login",
            data={
                "username": test_admin_user["email"],
                "password": test_admin_user["password"],
            },
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert response.json() == {"detail": "Invalid password"}

    @patch("app.services.auth.Auth.decode_refresh_token", new_callable=AsyncMock)
    @patch("app.repository.users.get_user_by_email", new_callable=AsyncMock)
    @patch("app.services.auth.Auth.create_access_token", new_callable=AsyncMock)
    @patch("app.services.auth.Auth.create_refresh_token", new_callable=AsyncMock)
    @patch("app.repository.users.update_token", new_callable=AsyncMock)
    async def test_refresh_token_valid(
        self,
        mock_update,
        mock_refresh,
        mock_access,
        mock_get_user_by_email,
        mock_decode_refresh,
        client: TestClient,
        get_refresh_admin,
    ):
        mock_update.return_value = Mock()
        mock_refresh.return_value = "new_refresh_token"
        mock_access.return_value = "access_token"
        mock_get_user_by_email.return_value = Mock(refresh_token=get_refresh_admin)
        mock_decode_refresh.return_value = "email1@example.com"
        headers = {"Authorization": f"Bearer {get_refresh_admin}"}
        response = client.get("/api/auth/refresh_token", headers=headers)

        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"

    @patch("app.services.auth.Auth.decode_refresh_token", new_callable=AsyncMock)
    @patch("app.repository.users.get_user_by_email", new_callable=AsyncMock)
    async def test_refresh_token_invalid(
        self,
        mock_get_user_by_email,
        mock_decode_refresh,
        client: TestClient,
        get_refresh_admin,
    ):
        mock_get_user_by_email.return_value = Mock(
            refresh_token="invalid_refresh_token"
        )
        mock_decode_refresh.return_value = "email1@example.com"

        headers = {"Authorization": "Bearer invalid_token"}
        response = client.get("/api/auth/refresh_token", headers=headers)

        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert response.json() == {"detail": "Invalid refresh token"}

    @patch("app.services.auth.Auth.verify_email_token", new_callable=AsyncMock)
    @patch("app.repository.users.get_user_by_email", new_callable=AsyncMock)
    @patch("app.repository.users.confirmed_email", new_callable=AsyncMock)
    async def test_confirmed_email_valid(
        self,
        mock_confirmed_email,
        mock_get_user_by_email,
        mock_verify_email_token,
        client: TestClient,
    ):
        mock_confirmed_email.return_value = Mock()
        mock_verify_email_token.return_value = "mock@email.com"
        mock_get_user_by_email.return_value = SimpleNamespace(
            **{"username": "mock_username", "verified": False}
        )
        response = client.get("/api/auth/confirmed_email/valid_token")

        assert response.status_code == status.HTTP_200_OK
        assert response.json() == {"message": "Email confirmed"}

    @patch("app.services.auth.Auth.verify_email_token", new_callable=AsyncMock)
    @patch("app.repository.users.get_user_by_email", new_callable=AsyncMock)
    async def test_confirmed_email_bad_request(
        self, mock_get_user_by_email, mock_verify_email_token, client: TestClient
    ):
        mock_verify_email_token.return_value = "mock@email.com"
        mock_get_user_by_email.return_value = None
        response = client.get("/api/auth/confirmed_email/invalid_token")

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.json() == {"detail": "Verification error"}

    @patch("app.services.auth.Auth.verify_email_token", new_callable=AsyncMock)
    @patch("app.repository.users.get_user_by_email", new_callable=AsyncMock)
    async def test_confirmed_email_already(
        self, mock_get_user_by_email, mock_verify_email_token, client: TestClient
    ):
        mock_verify_email_token.return_value = "mock@email.com"
        mock_get_user_by_email.return_value = SimpleNamespace(
            **{"username": "mock_username", "verified": True}
        )
        response = client.get("/api/auth/confirmed_email/invalid_token")

        assert response.status_code == status.HTTP_200_OK
        assert response.json() == {"message": "Your email is already confirmed"}

    @patch("app.routes.auth.BackgroundTasks.add_task", new_callable=Mock)
    @patch("app.repository.users.get_user_by_email", new_callable=AsyncMock)
    async def test_request_email(self, mock_get_user_by_email, bt, client: TestClient):
        mock_get_user_by_email.return_value = SimpleNamespace(
            **{"email": "mock@email.com", "username": "mock", "verified": False}
        )
        bt.return_value = Mock()
        response = client.post(
            "/api/auth/request_email", json={"email": "mock@email.com"}
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.json() == {"message": "Check your email for confirmation."}

    @patch("app.repository.users.get_user_by_email", new_callable=AsyncMock)
    async def test_request_email(self, mock_get_user_by_email, client: TestClient):
        mock_get_user_by_email.return_value = SimpleNamespace(
            **{"email": "mock@email.com", "username": "mock", "verified": True}
        )

        response = client.post(
            "/api/auth/request_email", json={"email": "mock@email.com"}
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.json() == {"message": "Your email is already confirmed"}

    @patch("app.repository.users.get_user_by_email", new_callable=AsyncMock)
    async def test_request_email(self, mock_get_user_by_email, client: TestClient):
        mock_get_user_by_email.return_value = None

        response = client.post(
            "/api/auth/request_email", json={"email": "mock@email.com"}
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.json() == {"message": "User is`t exist"}


@pytest.mark.asyncio
class TestUserProfile:
    @patch("app.routes.user_profile.RateLimiter.__call__", new_callable=AsyncMock)
    @patch(
        "app.services.cloudinary.Cloudinary.upload_avatar_to_cloudinary",
        new_callable=AsyncMock,
    )
    @patch("app.repository.users.update_avatar_url", new_callable=AsyncMock)
    async def test_update_avatar(
        self,
        mock_update_avatar_url,
        mock_upload_avatar_to_cloudinary,
        mock_rate_limiter,
        mock_auth_settings,
        get_token_admin,
        client: TestClient,
    ):
        mock_rate_limiter.return_value = True
        mock_update_avatar_url.return_value = Mock()
        mock_upload_avatar_to_cloudinary.return_value = "mock_url"
        file_content = io.BytesIO(b"fake_image_content")
        file_content.name = "avatar.jpg"
        file_content = io.BytesIO(b"fake_image_content")

        response = client.post(
            "/api/profile/update_avatar",
            headers={"Authorization": f"Bearer {get_token_admin}"},
            files={"file": ("avatar.jpg", file_content, "image/jpeg")},
            params={
                "args": "value_for_args",
                "kwargs": "value_for_kwargs",
            },
        )

        print(response.json())
        assert response.status_code == status.HTTP_200_OK
        assert response.json() == {"message": "Avatar updated successfully!"}


@pytest.mark.asyncio
class TestContacts(TestFixtures):
    @patch("app.routes.user_profile.RateLimiter.__call__", new_callable=AsyncMock)
    @patch("app.repository.contacts.get_contacts", new_callable=AsyncMock)
    @patch("app.repository.contacts.set_contact_to_cache", new_callable=AsyncMock)
    @patch(
        "app.repository.contacts.get_all_contacts_from_cache", new_callable=AsyncMock
    )
    async def test_get_contacts_cached(
        self,
        mock_get_all_contacts_from_cache,
        mock_set_contact_to_cache,
        mock_get_contacts,
        mock_rate_limiter,
        setup_contacts,
        client,
        mock_auth_settings,
        get_token_admin,
    ):
        mock_rate_limiter.return_value = True
        mock_get_all_contacts_from_cache.return_value = None
        mock_get_contacts.return_value = setup_contacts
        mock_set_contact_to_cache.return_value = Mock()
        headers = {"Authorization": f"Bearer {get_token_admin}"}
        response = client.get(
            "/api/contacts/contact/?limit=10&offset=0",
            headers=headers,
            params={
                "args": "value_for_args",
                "kwargs": "value_for_kwargs",
            },
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.json()[0]["name"] == setup_contacts[0].name

    @patch("app.routes.user_profile.RateLimiter.__call__", new_callable=AsyncMock)
    @patch("app.repository.contacts.search_by", new_callable=AsyncMock)
    async def test_search_by_successful(
        self,
        mock_search_by,
        mock_rate_limiter,
        setup_contacts,
        client,
        mock_auth_settings,
        get_token_admin,
    ):
        mock_rate_limiter.return_value = True
        mock_search_by.return_value = setup_contacts

        headers = {"Authorization": f"Bearer {get_token_admin}"}
        response = client.get(
            "/api/contacts/search_by/",
            headers=headers,
            params={
                "args": "value_for_args",
                "kwargs": "value_for_kwargs",
            },
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.json()[0]["name"] == setup_contacts[0].name

    @patch("app.routes.user_profile.RateLimiter.__call__", new_callable=AsyncMock)
    @patch("app.repository.contacts.search_by", new_callable=AsyncMock)
    async def test_search_by_fail(
        self,
        mock_search_by,
        mock_rate_limiter,
        client,
        mock_auth_settings,
        get_token_admin,
    ):
        mock_rate_limiter.return_value = True
        mock_search_by.return_value = None

        headers = {"Authorization": f"Bearer {get_token_admin}"}
        response = client.get(
            "/api/contacts/search_by/",
            headers=headers,
            params={
                "args": "value_for_args",
                "kwargs": "value_for_kwargs",
            },
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert response.json() == {"detail": "NOT FOUND"}

    @patch("app.routes.user_profile.RateLimiter.__call__", new_callable=AsyncMock)
    @patch("app.repository.contacts.get_contact_from_cache", new_callable=AsyncMock)
    async def test_get_contact_cached(
        self,
        mock_get_contact_from_cache,
        mock_rate_limiter,
        setup_contacts,
        client,
        mock_auth_settings,
        get_token_admin,
    ):
        mock_rate_limiter.return_value = True
        mock_get_contact_from_cache.return_value = setup_contacts[0]

        headers = {"Authorization": f"Bearer {get_token_admin}"}
        response = client.get(
            "/api/contacts/contact/1",
            headers=headers,
            params={
                "args": "value_for_args",
                "kwargs": "value_for_kwargs",
            },
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["name"] == setup_contacts[0].name

    @patch("app.routes.user_profile.RateLimiter.__call__", new_callable=AsyncMock)
    @patch("app.repository.contacts.get_contact_from_cache", new_callable=AsyncMock)
    @patch("app.repository.contacts.get_contact", new_callable=AsyncMock)
    async def test_get_contact_not_found(
        self,
        mock_get_contact,
        mock_get_contact_from_cache,
        mock_rate_limiter,
        client,
        mock_auth_settings,
        get_token_admin,
    ):
        mock_rate_limiter.return_value = True
        mock_get_contact_from_cache.return_value = None
        mock_get_contact.return_value = None

        headers = {"Authorization": f"Bearer {get_token_admin}"}
        response = client.get(
            "/api/contacts/contact/1",
            headers=headers,
            params={
                "args": "value_for_args",
                "kwargs": "value_for_kwargs",
            },
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert response.json() == {"detail": "NOT FOUND"}

    @patch("app.routes.user_profile.RateLimiter.__call__", new_callable=AsyncMock)
    @patch("app.repository.contacts.get_contact_from_cache", new_callable=AsyncMock)
    @patch("app.repository.contacts.get_contact", new_callable=AsyncMock)
    @patch("app.repository.contacts.set_contact_to_cache", new_callable=AsyncMock)
    async def test_get_contact_from_db(
        self,
        mock_set_contact_to_cache,
        mock_get_contact,
        mock_get_contact_from_cache,
        mock_rate_limiter,
        client,
        setup_contacts,
        mock_auth_settings,
        get_token_admin,
    ):
        mock_rate_limiter.return_value = True
        mock_get_contact_from_cache.return_value = None
        mock_get_contact.return_value = setup_contacts[0]
        mock_set_contact_to_cache.return_value = Mock()

        headers = {"Authorization": f"Bearer {get_token_admin}"}
        response = client.get(
            "/api/contacts/contact/1",
            headers=headers,
            params={
                "args": "value_for_args",
                "kwargs": "value_for_kwargs",
            },
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["name"] == setup_contacts[0].name

    @patch("app.routes.user_profile.RateLimiter.__call__", new_callable=AsyncMock)
    @patch("app.repository.contacts.create_contacts", new_callable=AsyncMock)
    async def test_create_contact(
        self,
        mock_create_contacts,
        mock_rate_limiter,
        client,
        setup_contacts,
        mock_auth_settings,
        get_token_admin,
    ):
        def mock_to_dict(mock_obj):
            return {
                key: value
                for key, value in mock_obj.__dict__.items()
                if not key.startswith("_")
            }

        body = mock_to_dict(setup_contacts[0])

        mock_rate_limiter.return_value = True
        mock_create_contacts.return_value = setup_contacts[0]

        headers = {"Authorization": f"Bearer {get_token_admin}"}
        response = client.post(
            "/api/contacts/contact/",
            headers=headers,
            json=body,
            params={
                "args": "value_for_args",
                "kwargs": "value_for_kwargs",
            },
        )
        assert response.status_code == status.HTTP_201_CREATED
        assert response.json()["name"] == setup_contacts[0].name

    @patch("app.routes.user_profile.RateLimiter.__call__", new_callable=AsyncMock)
    @patch("app.repository.contacts.update_contacts", new_callable=AsyncMock)
    async def test_update_contact_successful(
        self,
        mock_update_contacts,
        mock_rate_limiter,
        client,
        setup_dict_contacts,
        mock_auth_settings,
        get_token_admin,
    ):
        mock_rate_limiter.return_value = True
        mock_update_contacts.return_value = setup_dict_contacts

        headers = {"Authorization": f"Bearer {get_token_admin}"}
        response = client.put(
            "/api/contacts/contact/1",
            headers=headers,
            json=setup_dict_contacts,
            params={
                "args": "value_for_args",
                "kwargs": "value_for_kwargs",
            },
        )
        print(response.json())
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["name"] == setup_dict_contacts["name"]

    @patch("app.routes.user_profile.RateLimiter.__call__", new_callable=AsyncMock)
    @patch("app.repository.contacts.update_contacts", new_callable=AsyncMock)
    async def test_update_contact_fail(
        self,
        mock_update_contacts,
        mock_rate_limiter,
        client,
        setup_dict_contacts,
        mock_auth_settings,
        get_token_admin,
    ):
        mock_rate_limiter.return_value = True
        mock_update_contacts.return_value = None

        headers = {"Authorization": f"Bearer {get_token_admin}"}
        response = client.put(
            "/api/contacts/contact/1",
            headers=headers,
            json=setup_dict_contacts,
            params={
                "args": "value_for_args",
                "kwargs": "value_for_kwargs",
            },
        )
        print(response.json())
        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert response.json() == {"detail": "NOT FOUND"}

    @patch("app.routes.user_profile.RateLimiter.__call__", new_callable=AsyncMock)
    @patch("app.repository.contacts.delete_contact", new_callable=AsyncMock)
    async def test_delete_contact(
        self,
        mock_delete_contact,
        mock_rate_limiter,
        client,
        setup_dict_contacts,
        mock_auth_settings,
        get_token_admin,
    ):
        mock_rate_limiter.return_value = True
        mock_delete_contact.return_value = setup_dict_contacts

        headers = {"Authorization": f"Bearer {get_token_admin}"}
        response = client.delete(
            "/api/contacts/contact/1",
            headers=headers,
            params={
                "args": "value_for_args",
                "kwargs": "value_for_kwargs",
            },
        )
        assert response.status_code == status.HTTP_204_NO_CONTENT

    @patch("app.routes.user_profile.RateLimiter.__call__", new_callable=AsyncMock)
    @patch(
        "app.repository.contacts.get_all_contacts_from_cache", new_callable=AsyncMock
    )
    async def test_get_birthdays_cached(
        self,
        mock_get_all_contacts_from_cache,
        mock_rate_limiter,
        setup_contacts,
        client,
        mock_auth_settings,
        get_token_admin,
    ):
        mock_rate_limiter.return_value = True
        mock_get_all_contacts_from_cache.return_value = setup_contacts

        headers = {"Authorization": f"Bearer {get_token_admin}"}
        response = client.get(
            "/api/contacts/birthdays",
            headers=headers,
            params={
                "args": "value_for_args",
                "kwargs": "value_for_kwargs",
            },
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.json()[0]["name"] == setup_contacts[0].name

    @patch("app.routes.user_profile.RateLimiter.__call__", new_callable=AsyncMock)
    @patch("app.repository.contacts.get_upcoming_birthdays", new_callable=AsyncMock)
    @patch(
        "app.repository.contacts.get_all_contacts_from_cache",
        new_callable=AsyncMock,
    )
    async def test_get_birthdays_not_found(
        self,
        mock_mock_get_all_contacts_from_cache,
        mock_get_upcoming_birthdays,
        mock_rate_limiter,
        client,
        mock_auth_settings,
        get_token_admin,
    ):
        mock_rate_limiter.return_value = True
        mock_get_upcoming_birthdays.return_value = None
        mock_mock_get_all_contacts_from_cache.return_value = None

        headers = {"Authorization": f"Bearer {get_token_admin}"}
        response = client.get(
            "/api/contacts/birthdays",
            headers=headers,
            params={
                "args": "value_for_args",
                "kwargs": "value_for_kwargs",
            },
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert response.json() == {"detail": "No upcoming birthdays found"}

    @patch("app.routes.user_profile.RateLimiter.__call__", new_callable=AsyncMock)
    @patch(
        "app.repository.contacts.get_all_contacts_from_cache", new_callable=AsyncMock
    )
    @patch("app.repository.contacts.get_upcoming_birthdays", new_callable=AsyncMock)
    @patch("app.repository.contacts.set_contact_to_cache", new_callable=AsyncMock)
    async def test_get_birthdays_from_db(
        self,
        mock_set_contact_to_cache,
        mock_get_upcoming_birthdays,
        mock_get_all_contacts_from_cache,
        mock_rate_limiter,
        client,
        setup_contacts,
        mock_auth_settings,
        get_token_admin,
    ):
        mock_rate_limiter.return_value = True
        mock_get_all_contacts_from_cache.return_value = None
        mock_get_upcoming_birthdays.return_value = setup_contacts
        mock_set_contact_to_cache.return_value = Mock()

        headers = {"Authorization": f"Bearer {get_token_admin}"}
        response = client.get(
            "/api/contacts/birthdays",
            headers=headers,
            params={
                "args": "value_for_args",
                "kwargs": "value_for_kwargs",
            },
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.json()[0]["name"] == setup_contacts[0].name
