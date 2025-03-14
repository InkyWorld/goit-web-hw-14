import enum
from datetime import datetime, date

from sqlalchemy import Boolean, String, Integer, DateTime, ForeignKey, Enum, Date, func
from sqlalchemy.orm import relationship, mapped_column, Mapped, DeclarativeBase


class Base(DeclarativeBase):
    pass


class Role(enum.Enum):
    admin = "admin"
    moderator = "moderator"
    user = "user"


class Contact(Base):
    __tablename__ = "contacts"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), index=True)
    surname: Mapped[str] = mapped_column(String(100), index=True)
    email: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    phone: Mapped[str] = mapped_column(String(20))
    date_of_birth: Mapped[date] = mapped_column(Date)
    additional_info: Mapped[str] = mapped_column(String(255), nullable=True)

    created_at: Mapped[date] = mapped_column(
        "created_at", DateTime, default=func.now(), nullable=True
    )
    updated_at: Mapped[date] = mapped_column(
        "updated_at", DateTime, default=func.now(), onupdate=func.now(), nullable=True
    )

    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", name="fk_user"), nullable=True
    )
    user: Mapped["User"] = relationship("User", backref="todos", lazy="joined")

    def __getstate__(self):
        """
        Метод для сериализации объекта в JSON. Сохраняем данные в словарь.
        """
        state = {
            "id": self.id,
            "name": self.name,
            "surname": self.surname,
            "email": self.email,
            "phone": self.phone,
            "date_of_birth": self.date_of_birth.isoformat() if self.date_of_birth else None,
            "additional_info": self.additional_info,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "user_id": self.user_id
        }
        return state

    def __setstate__(self, state):
        """
        Метод для десериализации из JSON.
        Восстанавливаем данные из словаря.
        """
        self.id = state.get("id")
        self.name = state.get("name")
        self.surname = state.get("surname")
        self.email = state.get("email")
        self.phone = state.get("phone")
        self.date_of_birth = state.get("date_of_birth")
        self.date_of_birth = date.fromisoformat(self.date_of_birth) if self.date_of_birth else None
        self.additional_info = state.get("additional_info")
        
        # For created_at and updated_at, use datetime instead of date
        self.created_at = state.get("created_at")
        if self.created_at:
            self.created_at = datetime.fromisoformat(self.created_at)
        
        self.updated_at = state.get("updated_at")
        if self.updated_at:
            self.updated_at = datetime.fromisoformat(self.updated_at)

        self.user_id = state.get("user_id")


class Role(enum.Enum):
    admin: str = "admin"
    moderator: str = "moderator"
    user: str = "user"


class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(50))
    email: Mapped[str] = mapped_column(String(150), nullable=False, unique=True)
    password: Mapped[str] = mapped_column(String(255), nullable=False)
    verified: Mapped[bool] = mapped_column(Boolean, default=False)
    avatar: Mapped[str] = mapped_column(String(2083), nullable=True)
    refresh_token: Mapped[str] = mapped_column(String(255), nullable=True)
    created_at: Mapped[date] = mapped_column("created_at", DateTime, default=func.now())
    updated_at: Mapped[date] = mapped_column(
        "updated_at", DateTime, default=func.now(), onupdate=func.now()
    )
    role: Mapped[Enum] = mapped_column(
        "role", Enum(Role), default=Role.user, nullable=True
    )
