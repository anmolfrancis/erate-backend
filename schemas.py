from pydantic import BaseModel

class UserCreate(BaseModel):
    email: str
    password: str
    user_type: str

class ShopCreate(BaseModel):
    name: str
    location: str
    latitude: float
    longitude: float
    food_type: str
    contact: str
    owner_email: str


class RatingCreate(BaseModel):
    customer_email: str
    shop_id: str
    food_quality: int
    hygiene: int
    service: int
    value_for_money: int
    overall_experience: int
    customer_lat: float
    customer_lon: float
