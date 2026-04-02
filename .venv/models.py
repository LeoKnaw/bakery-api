from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy import Column, String, Float, ForeignKey, Integer, DateTime, Boolean
from sqlalchemy.orm import relationship
from datetime import datetime
from database import Base
import uuid


class Product(Base):
    __tablename__ = "products"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, nullable=False)
    price = Column(Float, nullable=False)
    is_active = Column(Boolean, default=True)


class Production(Base):
    __tablename__ = "production"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    product_id = Column(UUID(as_uuid=True), ForeignKey("products.id"), nullable=False)
    quantity = Column(Integer, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)

    product = relationship("Product")


class Sale(Base):
    __tablename__ = "sales"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    timestamp = Column(DateTime, default=datetime.utcnow)

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
