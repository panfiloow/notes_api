from pydantic import BaseModel, model_validator
from datetime import datetime
from typing import Optional

class CreateNote(BaseModel):
    title: str
    content: Optional[str] = None

class UpdateNote(BaseModel):
    title: Optional[str] = None
    content: Optional[str] = None

    @model_validator(mode='after')
    def validate_at_least_one_field(self):
        if self.title is None and self.content is None:
            raise ValueError('At least one of "title" or "content" must be provided and not None.')
        return self 

class Note(CreateNote):
    id: int
    created_at: datetime
    updated_at: datetime

