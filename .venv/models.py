from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy import (
    Column,
    String,
    Float,
    ForeignKey,
    Integer,
    DateTime,
    Boolean,
    Date,
)
from sqlalchemy.orm import relationship
from datetime import datetime, timezone, timedelta, date
from database import Base
import uuid

# Nigerian Time (WAT - West Africa Time) = UTC+1
NIGERIAN_TZ = timezone(timedelta(hours=1))


def nigerian_now():
    """Return current time in Nigerian timezone as naive datetime."""
    return datetime.now(NIGERIAN_TZ).replace(tzinfo=None)


class Product(Base):
    __tablename__ = "products"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, nullable=False)
    price = Column(Float, nullable=False)
    wholesale_price = Column(Float, nullable=True)
    is_active = Column(Boolean, default=True)


class Production(Base):
    __tablename__ = "production"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    product_id = Column(UUID(as_uuid=True), ForeignKey("products.id"), nullable=False)
    quantity = Column(Integer, nullable=False)
    timestamp = Column(DateTime, default=nigerian_now)

    product = relationship("Product")


class Sale(Base):
    __tablename__ = "sales"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    timestamp = Column(DateTime, default=nigerian_now)

    items = relationship("SaleItem", back_populates="sale")


class SaleItem(Base):
    __tablename__ = "sale_items"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    sale_id = Column(UUID(as_uuid=True), ForeignKey("sales.id"), nullable=False)
    product_id = Column(UUID(as_uuid=True), ForeignKey("products.id"), nullable=False)
    quantity = Column(Integer, nullable=False)
    price = Column(Float, nullable=False)
    sale_type = Column(String, default="retail")  # retail, wholesale, supply

    sale = relationship("Sale", back_populates="items")
    product = relationship("Product")


class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    username = Column(String, unique=True, nullable=False)
    password_hash = Column(String, nullable=False)
    is_approved = Column(Boolean, default=False)
    is_admin = Column(Boolean, default=False)
    created_at = Column(DateTime, default=nigerian_now)


class DailyStockRecord(Base):
    __tablename__ = "daily_stock_records"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    record_date = Column(Date, nullable=False, index=True)
    product_id = Column(UUID(as_uuid=True), ForeignKey("products.id"), nullable=False)
    opening_stock = Column(Integer, default=0)
    production_stock = Column(Integer, default=0)
    wholesale_quantity = Column(Integer, default=0)
    retail_quantity = Column(Integer, default=0)
    supply_quantity = Column(Integer, default=0)
    wholesale_revenue = Column(Float, default=0.0)
    retail_revenue = Column(Float, default=0.0)
    closing_stock = Column(Integer, default=0)
    created_at = Column(DateTime, default=nigerian_now)
    updated_at = Column(DateTime, default=nigerian_now, onupdate=nigerian_now)

    product = relationship("Product")
