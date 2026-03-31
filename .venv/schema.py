from pydantic import BaseModel, Field, computed_field
from typing import Optional, List
from uuid import UUID
from database import Base
from datetime import datetime
import os
from dotenv import load_dotenv


# Product Schema
class Product(BaseModel):
    __tablename__ = "products"
    name: str
    price: float = Field(gt=0)


class ProductCreate(Product):
    pass


class ProductResponse(Product):
    id: UUID

    @computed_field
    @property
    def wholesale_price(self) -> float:
        return self.price * 0.9

    class Config:
        from_attributes = True


class ProductUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1)
    price: Optional[float] = Field(gt=0)


# Production Schema


class ProductInfo(BaseModel):
    id: UUID
    name: str

    class Config:
        from_attributes = True


class ProductionCreate(BaseModel):
    product_id: UUID
    quantity: int = Field(gt=0)

    class Config:
        from_attributes = True


class ProductionRecord(BaseModel):
    id: UUID
    product: ProductInfo
    quantity: int = Field(gt=0)
    timestamp: datetime = Field(default_factory=datetime.now)

    class Config:
        from_attributes = True


class SaleItemCreate(BaseModel):
    product_id: UUID
    quantity: int
    sale_type: str = "retail"  # retail, wholesale, supply


class SaleCreate(BaseModel):
    items: list[SaleItemCreate]
