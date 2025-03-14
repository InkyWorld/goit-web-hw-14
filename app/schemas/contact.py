from pydantic import BaseModel, Field, EmailStr, field_validator
from datetime import datetime
from typing import Optional, Annotated
from datetime import date

class ContactSchema(BaseModel):
    name: Annotated[str, Field(min_length=1, max_length=100)]
    surname: Annotated[str, Field(min_length=1, max_length=100)]
    email: Annotated[EmailStr, Field(max_length=100)]
    phone: Annotated[str, Field(pattern=r"^((?<full>(\+?38)[-\s\(\.]?\d{3}[-\s\)\.]?)|(?<short>[\.(]?0\d{2}[\.)]?))?[-\s\.]?\d{3}[-\s\.]?\d{2}[-\s\.]?\d{2}$")]
    date_of_birth: Annotated[str, Field()]
    additional_info: Optional[Annotated[str, Field(max_length=255)]] = None

    @field_validator('date_of_birth')
    def validate_date_of_birth(cls, v):
        if isinstance(v, str):  # Convert string to date
            try:
                datetime.strptime(v, '%Y-%m-%d')
            except ValueError:
                raise ValueError(f'Невірний формат дати: {v}. Має бути у форматі Y-M-D ')
        return v
        
    

class ContactUpdateSchema(ContactSchema):
    completed: bool


class ContactResponseSchema(ContactSchema):
    id: int = 1
    date_of_birth: date  


    class Config:
        json_encoders = {
            date: lambda v: v.strftime('%Y-%m-%d')  # Format date as 'YYYY-MM-DD'
        }
        from_attributes = True


