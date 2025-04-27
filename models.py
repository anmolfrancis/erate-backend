from pydantic import BaseModel
from typing import Optional

class User(BaseModel):
    email: str
    password: str
    user_type: str  # 'customer' or 'shop_owner'

class Shop(BaseModel):
    id: str
    name: str
    location: str
    latitude: float
    longitude: float
    food_type: str
    contact: str
    owner_email: str
    qr_code_path: str

class Rating(BaseModel):
    customer_email: str
    shop_id: str
    food_quality: int
    hygiene: int
    service: int
    value_for_money: int
    overall_experience: int
    customer_lat: Optional[float]
    customer_lon: Optional[float]
