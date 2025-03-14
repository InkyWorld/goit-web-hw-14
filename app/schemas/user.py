from abc import ABC

from typing import Annotated


from pydantic import BaseModel, Field, EmailStr

class AbstractUserSchema(BaseModel, ABC):
    username: Annotated[str, Field(min_length=1, max_length=50)]
    email: EmailStr
    

class UserResponseSchema(AbstractUserSchema):
    pass

class UserCreationSchema(AbstractUserSchema):
    password: Annotated[str, Field(min_length=6, max_length=15)]


class TokenSchema(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"

class RequestEmail(BaseModel):
    email: EmailStr