from unittest.mock import AsyncMock, MagicMock, patch
from fastapi import FastAPI, HTTPException, status
from fastapi.testclient import TestClient
from httpx import AsyncClient
import pytest
from main import app, lifespan
from conftest import user, admin
from app.services.auth import Auth
from sqlalchemy.ext.asyncio import AsyncSession


@pytest.mark.asyncio
class TestMainAsync:
    async def test_admin_forbidden_access(self, mock_auth_settings, client: TestClient, get_token_not_admin: str):
        response = client.get(
            "/admin", headers={"Authorization": f"Bearer {get_token_not_admin}"}
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert response.json() == {"detail": "FORBIDDEN"}
    
    async def test_admin_access(self, mock_auth_settings, client: TestClient, get_token_admin: str):
        response = client.get(
            "/admin", headers={"Authorization": f"Bearer {get_token_admin}"}
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.json() == {"message": "you admin!"}



    async def test_lifespan(self):
        with patch(
            "main.redis_manager.connect", new_callable=AsyncMock
        ) as mock_connect, patch("main.redis_manager.session") as mock_session, patch(
            "main.redis_manager.close", new_callable=AsyncMock
        ) as mock_close, patch(
            "main.FastAPILimiter.init", new_callable=AsyncMock
        ) as mock_limiter_init, patch(
            "main.FastAPILimiter.close", new_callable=AsyncMock
        ) as mock_limiter_close:

            # Set up __aenter__ to return an AsyncMock (redis object)
            mock_session.__aenter__.return_value = AsyncMock()
            mock_session.__aexit__.return_value = AsyncMock()

            # Симуляция работы lifespan
            async with lifespan(app):
                pass

            # Assertions or checks (if any)
            mock_connect.assert_awaited_once()
            mock_session.assert_called_once()
            mock_close.assert_awaited_once()
            mock_limiter_init.assert_awaited_once()
            mock_limiter_close.assert_awaited_once()



    async def test_health_checker(self, client: TestClient):

        response = client.get("/api/health_checker")

        # Check that the response is successful
        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "Database is connected and healthy"
        assert data["result"] == 1

