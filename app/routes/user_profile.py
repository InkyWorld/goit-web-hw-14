from fastapi import (
    APIRouter,
    File,
    Depends,
    UploadFile,
    BackgroundTasks,
)

from sqlalchemy.ext.asyncio import AsyncSession

from app.database.db import get_db
from app.repository import users as repositories_users

from app.services.auth import auth_service
from fastapi_limiter.depends import RateLimiter
from app.services.cloudinary import claudinary

profile_router = APIRouter(prefix="/profile", tags=["profile"])


@profile_router.post(
    "/update_avatar", dependencies=[Depends(RateLimiter(times=1, seconds=20))]
)
async def update_avatar(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    user=Depends(auth_service.authenticate_user),
):
    """
    Endpoint to update the user's avatar.

    This endpoint allows an authenticated user to upload a new avatar image. The image is 
    uploaded to Cloudinary and the URL of the uploaded image is then saved in the database 
    for the corresponding user.

    Args:
        file (UploadFile): The image file to upload, received from the client.
        db (AsyncSession): The database session used to interact with the database.
        user (User): The authenticated user (automatically injected by the `authenticate_user` method).

    Returns:
        dict: A JSON response with a success message.

    Raises:
        HTTPException: If the file upload to Cloudinary fails, or if there is an issue with updating the avatar in the database.
        RateLimiterException: If the rate limit (1 request per 20 seconds) is exceeded.
    """
    result_url =  await claudinary.upload_avatar_to_cloudinary(file, user.email)
    await repositories_users.update_avatar_url(user.email, result_url, db)
    return {"message": "Avatar updated successfully!"}


