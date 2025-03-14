import os
from pathlib import Path
from typing import Optional
from pydantic import ConfigDict, EmailStr
from pydantic_settings import BaseSettings


BASE_DIR = Path(__file__).resolve().parent.parent.parent


class Settings(BaseSettings):
    model_config = ConfigDict(
        extra="ignore",
        env_file=os.path.join(BASE_DIR, ".env"),
        env_file_encoding="utf-8",
    )


class DBConfig(Settings):
    DATABASE_URL: str = "postgresql+asyncpg://postgres:111111@localhost:5432/abc"


class RedisConfig(Settings):
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_PASSWORD: Optional[str] = None
    REDIS_DB: int = 0


class CloudinaryConfig(Settings):
    CLOUDINARY_CLOUD_NAME: str = "abc"
    CLOUDINARY_API_KEY: str = "326488457974591"
    CLOUDINARY_API_SECRET: str = "secret"


class JWTConfig(Settings):
    SECRET_KEY: str = "1234567890"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7


class EmailConfig(Settings):
    MAIL_USERNAME: EmailStr = "email@meail.com"
    MAIL_PASSWORD: str = "password"
    MAIL_FROM: str = "user"
    MAIL_PORT: int = 465
    MAIL_SERVER: str = "server"
    MAIL_FROM_NAME: str = "example"
    MAIL_STARTTLS: bool
    MAIL_SSL_TLS: bool
    USE_CREDENTIALS: bool
    VALIDATE_CERTS: bool


db_config = DBConfig()
config_redis = RedisConfig()
cloudinary_config = CloudinaryConfig()
email_config = EmailConfig()
jwt_config = JWTConfig()
