from datetime import datetime, timedelta, timezone
import pickle
from typing import Any, Coroutine, Optional

from fastapi import Depends, HTTPException, status
from passlib.context import CryptContext
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession
from jose import JWTError, jwt
from redis.asyncio import Redis

from app.database.db import get_db
from app.database.redis import get_redis
from app.models.models import User
from app.repository import users as repository_users
from app.conf.config import jwt_config


class Auth:
    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
    SECRET_KEY = jwt_config.SECRET_KEY
    ALGORITHM = jwt_config.ALGORITHM
    ACCESS_TOKEN_EXPIRE_MINUTES = jwt_config.ACCESS_TOKEN_EXPIRE_MINUTES
    REFRESH_TOKEN_EXPIRE_DAYS = jwt_config.REFRESH_TOKEN_EXPIRE_DAYS
    oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/auth/login")

    def verify_password(self, plan_password, hashed_password):
        """
        Verifies if the provided plain password matches the hashed password.

        Args:
            plain_password (str): The plain password to verify.
            hashed_password (str): The hashed password to compare against.

        Returns:
            bool: `True` if passwords match, otherwise `False`.
        """
        return self.pwd_context.verify(plan_password, hashed_password)

    def get_password_hash(self, password):
        """
        Generates a hashed password from the plain password.

        Args:
            password (str): The plain password to hash.

        Returns:
            str: The hashed password.
        """
        return self.pwd_context.hash(password)

    async def create_access_token(
        self, data: dict, expires_delta: Optional[timedelta] = None
    ):
        """
        Creates an access token encoded as a JWT.

        Args:
            data (dict): The data to encode in the token.
            expires_delta (Optional[timedelta]): The expiration time of the token. Defaults to `None`.

        Returns:
            str: The encoded JWT access token.
        """
        to_encode = data.copy()
        if expires_delta:
            expire = datetime.now(timezone.utc) + expires_delta
        else:
            expire = datetime.now(timezone.utc) + timedelta(
                minutes=self.ACCESS_TOKEN_EXPIRE_MINUTES
            )
        to_encode.update(
            {"iat": datetime.now(timezone.utc), "exp": expire, "scope": "access_token"}
        )
        encoded_access_token = jwt.encode(
            to_encode, self.SECRET_KEY, algorithm=self.ALGORITHM
        )
        return encoded_access_token

    async def create_refresh_token(
        self, data: dict, expires_delta: Optional[timedelta] = None
    ):
        """
        Creates a refresh token encoded as a JWT.

        Args:
            data (dict): The data to encode in the token.
            expires_delta (Optional[timedelta]): The expiration time of the token. Defaults to `None`.

        Returns:
            str: The encoded JWT refresh token.
        """
        to_encode = data.copy()
        if expires_delta:
            expire = datetime.now(timezone.utc) + expires_delta
        else:
            expire = datetime.now(timezone.utc) + timedelta(
                minutes=self.REFRESH_TOKEN_EXPIRE_DAYS
            )
        to_encode.update(
            {"iat": datetime.now(timezone.utc), "exp": expire, "scope": "refresh_token"}
        )
        encoded_access_token = jwt.encode(
            to_encode, self.SECRET_KEY, algorithm=self.ALGORITHM
        )
        return encoded_access_token

    async def decode_refresh_token(self, refresh_token: str):
        """
        Decodes and validates a refresh token to extract the user's email.

        Args:
            refresh_token (str): The refresh token to decode.

        Returns:
            str: The user's email associated with the refresh token.

        Raises:
            HTTPException: If the token is invalid or has the wrong scope.
        """
        try:
            payload = jwt.decode(
                refresh_token, self.SECRET_KEY, algorithms=[self.ALGORITHM]
            )
            if payload["scope"] == "refresh_token":
                email = payload["sub"]
                return email
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid scope for token",
            )
        except JWTError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not validate credential",
            )

    async def authenticate_user(
        self, token: str = Depends(oauth2_scheme), db: AsyncSession = Depends(get_db), redis: Redis = Depends(get_redis)
    ) -> Coroutine[Any, Any, User]:
        """
        Authenticates the user based on the provided access token.

        Args:
            token (str): The access token to authenticate the user.
            db (AsyncSession): The database session dependency.
            redis (Redis): The Redis dependency.

        Returns:
            User: The authenticated user object.

        Raises:
            HTTPException: If the token is invalid or expired.
        """
        credentials_exception = HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
        try:
            payload = jwt.decode(token, self.SECRET_KEY, algorithms=[self.ALGORITHM])
            print(payload)
            if payload["scope"] == "access_token":
                email = payload["sub"]
                if email is None:
                    raise credentials_exception
            else:
                raise credentials_exception
        except JWTError as e:
            raise credentials_exception
        user = await redis.get(f"user:{email}")
        if user is None:
            user = await repository_users.get_user_by_email(email, db)
            if user is None:
                raise credentials_exception
            await redis.set(f"user:{email}", pickle.dumps(user))
            await redis.expire(f"user:{email}", 900)
        else:
            user = pickle.loads(user)
        return user

    async def create_email_token(self, data: dict):
        """
        Creates an email verification token.

        Args:
            data (dict): The data to encode in the email verification token.

        Returns:
            str: The encoded email verification token.
        """
        to_encode = data.copy()
        expire = datetime.now(timezone.utc) + timedelta(days=1)
        to_encode.update({"iat": datetime.now(timezone.utc), "exp": expire})
        encoded_access_token = jwt.encode(
            to_encode, self.SECRET_KEY, algorithm=self.ALGORITHM
        )
        return encoded_access_token

    async def verify_email_token(self, token: str):
        """
        Verifies the provided email token.

        Args:
            token (str): The email verification token to verify.

        Returns:
            str: The email address associated with the token.

        Raises:
            HTTPException: If the token is invalid.
        """
        try:
            payload = jwt.decode(token, self.SECRET_KEY, algorithms=[self.ALGORITHM])
            return payload["sub"]
        except JWTError:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Invalid email verification token",
            )


auth_service = Auth()
