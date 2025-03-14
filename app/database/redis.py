from redis.asyncio import Redis
import contextlib
from app.conf.config import config_redis


class RedisSessionManager:
    def __init__(self, host: str, port: int, db: int, password: str | None = None):
        self._redis_client = Redis(
            host=host,
            port=port,
            db=db,
            password=password,
        )

    async def connect(self):
        """Опциональный метод, если нужно явно проверять подключение"""
        try:
            await self._redis_client.ping()
        except Exception as e:
            print(f"Ошибка подключения к Redis: {e}")
            
    async def close(self):
        if self._redis_client:
            await self._redis_client.close()

    @contextlib.asynccontextmanager
    async def session(self):
        if self._redis_client is None:
            raise Exception("Redis is not initialized")
        yield self._redis_client



# Створюємо глобальний об'єкт менеджера Redis
redis_manager = RedisSessionManager(
    host=config_redis.REDIS_HOST,
    port=config_redis.REDIS_PORT,
    db=config_redis.REDIS_DB,
    password=config_redis.REDIS_PASSWORD
)


async def get_redis():
    """Функція-залежність для отримання сесії Redis у FastAPI"""
    async with redis_manager.session() as redis:
        yield redis
