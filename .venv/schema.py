from pydantic import BaseModel, Field, computed_field
from typing import Optional, List
from uuid import UUID
from datetime import datetime, timezone, timedelta

# Nigerian Time (WAT - West Africa Time) = UTC+1
NIGERIAN_TZ = timezone(timedelta(hours=1))


def nigerian_now():
    """Return current time in Nigerian timezone as naive datetime."""
    return datetime.now(NIGERIAN_TZ).replace(tzinfo=None)


# Product Schema
class Product(BaseModel):
    __tablename__ = "products"
    name: str = Field(min_length=1, max_length=100)
    price: float = Field(gt=0, le=1000000)  # Max 1 million


class ProductCreate(Product):
    pass


class ProductResponse(Product):
    id: UUID
    is_active: bool = True

    @computed_field
    @property
    def wholesale_price(self) -> float:
        return self.price * 0.9

    class Config:
        from_attributes = True


class ProductUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=100)
    price: Optional[float] = Field(default=None, gt=0, le=1000000)


# Production Schema


class ProductInfo(BaseModel):
    id: UUID
    name: str

    class Config:
        from_attributes = True


class ProductionCreate(BaseModel):
    product_id: UUID
    quantity: int = Field(gt=0, le=100000)  # Max 100k units

    class Config:
        from_attributes = True


class ProductionRecord(BaseModel):
    id: UUID
    product: ProductInfo
    quantity: int = Field(gt=0)
    timestamp: datetime = Field(default_factory=nigerian_now)

    class Config:
        from_attributes = True


class SaleItemCreate(BaseModel):
    product_id: UUID
    quantity: int = Field(gt=0, le=100000)  # Max 100k units
    sale_type: str = Field(default="retail", pattern="^(retail|wholesale|supply)$")


class SaleCreate(BaseModel):
    items: List[SaleItemCreate] = Field(
        min_length=1, max_length=50
    )  # Max 50 items per sale


# User Auth Schemas
class UserRegister(BaseModel):
    username: str = Field(min_length=3, max_length=50)
    password: str = Field(min_length=6, max_length=100)


class UserLogin(BaseModel):
    username: str
    password: str


class UserResponse(BaseModel):
    id: UUID
    username: str
    is_approved: bool
    is_admin: bool
    created_at: datetime

    class Config:
        from_attributes = True


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    is_admin: bool
    is_approved: bool
