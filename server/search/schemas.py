from pydantic import BaseModel


class Like(BaseModel):
    user_id: str
    property_id: str
