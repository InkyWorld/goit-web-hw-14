from contextlib import asynccontextmanager
from typing import AsyncGenerator
from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi_limiter import FastAPILimiter
import redis.asyncio as redis
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.db import get_db
from app.models.models import Role
from app.routes.contacts import router_additional, router_crud
from app.routes.auth import auth_router
from app.routes.user_profile import profile_router
from app.services.roles import RoleAccess
from app.database.redis import redis_manager

admin_access = RoleAccess([Role.admin])


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    Lifespan function for managing the startup and shutdown lifecycle of the FastAPI application.
    
    This function is used to initialize and clean up the Redis connection and setup 
    the FastAPILimiter during the application's lifespan. It connects to Redis 
    when the app starts and closes the connection when the app shuts down.

    Args:
        app (FastAPI): The FastAPI application instance that will use this lifespan manager.

    Yields:
        None: This is a context manager, and the yielded value is unused. It simply
        marks the point where the application is running.
    
    Example:
        ```python
        app = FastAPI(lifespan=lifespan)
        ```
    """
    print("App starting up...")

    await redis_manager.connect()
    # Отримуємо сесію Redis для FastAPILimiter
    async with redis_manager.session() as redis:
        await FastAPILimiter.init(redis)

    yield
    print("App shutting down...")
    await redis_manager.close()
    await FastAPILimiter.close()



app = FastAPI(debug=True, lifespan=lifespan)

origins = [
    "http://localhost",  # Дозволяє запити з localhost
    "http://localhost:3000",  # frontend
]


app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router, prefix="/api")
app.include_router(router_additional, prefix="/api")
app.include_router(router_crud, prefix="/api")
app.include_router(profile_router, prefix="/api")


@app.get("/admin", dependencies=[Depends(admin_access)])
async def index():
    """
    Admin endpoint to verify admin access.

    This endpoint returns a message confirming the user has admin access. The route is protected 
    by the `admin_access` dependency, which ensures that only users with proper admin privileges 
    can access this endpoint. If the user does not have admin access, an error will be raised 
    by the `admin_access` dependency.

    Args:
        None: This function does not require any arguments directly.

    Returns:
        dict: A dictionary containing a message confirming the admin status.

    Raises:
        Depends: If the `admin_access` dependency fails (i.e., the user is not an admin), 
        an error will be raised.

    Example:
        ```python
        response = await client.get("/admin")
        assert response.status_code == 200
        assert response.json() == {"message": "you admin!"}
        ```
    """
    
    return JSONResponse(content={"message": "you admin!"})


@app.get("/api/health_checker")
async def health_checker(db: AsyncSession = Depends(get_db)):
    """
    Endpoint to check the health of the database connection.

    This endpoint performs a simple database query (`SELECT 1`) to verify if the database 
    is connected and configured correctly. If the query succeeds, a success message with 
    the result is returned. If the query fails or any other error occurs during the connection,
    an HTTP 500 error is raised with a message indicating the failure.

    Args:
        db (AsyncSession): The database session, injected by FastAPI's dependency system.

    Raises:
        HTTPException: If the database query fails or the database connection is not properly 
        configured, an HTTP 500 error is raised with an appropriate message.

    Returns:
        dict: A dictionary containing a health check message and the result of the query.

    Example:
        ```python
        response = await client.get("/api/health_checker")
        assert response.status_code == 200
        assert response.json() == {"message": "Database is connected and healthy", "result": 1}
        ```
    """
    try:
        # Make request
        result = await db.execute(text("SELECT 1"))
        result = result.fetchone()
        print(result)
        if result is None:
            raise HTTPException(
                status_code=500, detail="Database is not configured correctly"
            )

        return {"message": "Database is connected and healthy", "result": result[0]}

    except Exception as e:
        print(e)
        raise HTTPException(status_code=500, detail="Error connecting to the database")

