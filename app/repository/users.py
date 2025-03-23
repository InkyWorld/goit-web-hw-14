from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.db import get_db
from app.models.models import User
from app.schemas.user import UserCreationSchema
from sqlalchemy import select


async def get_user_by_email(email: str, db: AsyncSession = Depends(get_db)):
    """
    Retrieve a user by their email address.

    This function queries the database to find a user by their email address.

    Args:
        email (str): The email address of the user.
        db (AsyncSession, optional): The database session. Defaults to Depends(get_db).

    Returns:
        User | None: The user object if found, or None if the user does not exist.
    """
    stmt = select(User).filter(User.email == email)
    user = await db.execute(stmt)
    user = user.scalar_one_or_none()
    print(email)
    print(user, "======================")
    return user


async def create_user(body: UserCreationSchema, db: AsyncSession = Depends(get_db)):
    """
    Create a new user in the database.

    This function creates a new user by extracting the data from the provided
    UserCreationSchema and saving it to the database.

    Args:
        body (UserCreationSchema): The user creation data, including email and password.
        db (AsyncSession, optional): The database session. Defaults to Depends(get_db).

    Returns:
        User: The newly created user object.
    """
    print(db)
    user = User(**body.model_dump())
    await db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


async def update_token(user: User, token: str | None, db: AsyncSession):
    """
    Update the user's refresh token in the database.

    This function updates the user's refresh token with the new value provided.

    Args:
        user (User): The user object whose token is being updated.
        token (str | None): The new refresh token value. If None, the token will be cleared.
        db (AsyncSession): The database session to commit changes.
    """
    user.refresh_token = token
    await db.commit()


async def confirmed_email(email: str, db: AsyncSession) -> None:
    """
    Confirm a user's email address.

    This function sets the 'verified' status of the user to True after verifying
    their email address.

    Args:
        email (str): The email address of the user to be confirmed.
        db (AsyncSession): The database session to commit changes.

    Returns:
        None: This function does not return any value.
    """
    user = await get_user_by_email(email, db)
    if user:
        user.verified = True
        await db.commit()
    return user if user else None


async def update_avatar_url(email: str, url: str | None, db: AsyncSession) -> User:
    """
    Update the avatar URL for a user identified by their email.

    Args:
        email (str): The email of the user whose avatar URL needs to be updated.
        url (str | None): The new avatar URL. If `None`, the avatar is removed.
        db (AsyncSession): The database session used to interact with the database.

    Returns:
        User: The updated user object with the new avatar URL.

    Raises:
        ValueError: If the user with the provided email is not found in the database.
    """
    print("111111111111111111111111111111111111111")
    user = await get_user_by_email(email, db)
    user.avatar = url
    await db.commit()
    await db.refresh(user)
    return user
