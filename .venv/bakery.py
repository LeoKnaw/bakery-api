from fastapi import FastAPI, HTTPException, Depends
from fastapi.responses import HTMLResponse
from typing import Optional, List
from schema import (
    Product,
    ProductCreate,
    ProductResponse,
    ProductUpdate,
    ProductionCreate,
    ProductionRecord,
    SaleCreate,
    SaleItemCreate,
)
from models import Base, Product, Production, Sale, SaleItem
from database import Base, engine, SessionLocal
from uuid import uuid4, UUID
from sqlalchemy import func
from sqlalchemy.orm import Session
from datetime import datetime, date

app = FastAPI()
Base.metadata.create_all(bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@app.get("/fadel/products", response_model=List[ProductResponse])
async def get_products(db: Session = Depends(get_db)):
    return db.query(Product).all()


@app.post("/fadel/products", response_model=ProductResponse)
async def create_product(product: ProductCreate, db: Session = Depends(get_db)):
    db_product = Product(name=product.name, price=product.price)
    db.add(db_product)
    db.commit()
    db.refresh(db_product)
    return db_product


@app.put("/fadel/products/{product_id}", response_model=ProductResponse)
async def update_product(
    product_id: UUID, updated: ProductUpdate, db: Session = Depends(get_db)
):
    product = db.query(Product).filter(Product.id == product_id).first()

    if not product:
        raise HTTPException(status_code=404, detail=f"Product {product_id} not found")

    product.name = updated.name
    product.price = updated.price

    db.commit()
    db.refresh(product)
    return product


@app.delete("/fadel/delete/{product_id}")
async def delete_product(product_id: UUID, db: Session = Depends(get_db)):
    product = db.query(Product).filter(Product.id == product_id).first()

    if not product:
        raise HTTPException(status_code=404, detail=f"Product {product_id} not found")

    db.delete(product)
    db.commit()

    return None


# Production and inventory endpoints


# creating a new product. like baking a bread
@app.post("/fadel/production", response_model=ProductionRecord)
async def create_production(
    production: ProductionCreate, db: Session = Depends(get_db)
):
    product = (
        db.query(Product).filter(Product.id == production.product_id).first()
    )  # checking if it exists in the db
    if not product:
        raise HTTPException(
            status_code=404, detail=f"Product {production.product_id} not found"
        )

    db_prod = Production(product_id=production.product_id, quantity=production.quantity)
    db.add(db_prod)
    db.commit()
    db.refresh(db_prod)

    db_prod.product = product

    return db_prod


@app.get("/fadel/production", response_model=List[ProductionRecord])
async def get_production_records(db: Session = Depends(get_db)):
    return db.query(Production).all()


@app.post("/sales")
def create_sale(sale: SaleCreate, db: Session = Depends(get_db)):
    # First pass: validate all items have sufficient stock
    insufficient = []
    for item in sale.items:
        product = db.query(Product).filter(Product.id == item.product_id).first()
        if not product:
            raise HTTPException(status_code=404, detail="Product not found")

        # Check available stock
        current_stock = (
            db.query(func.coalesce(func.sum(Production.quantity), 0))
            .filter(Production.product_id == item.product_id)
            .scalar()
            - db.query(func.coalesce(func.sum(SaleItem.quantity), 0))
            .filter(SaleItem.product_id == item.product_id)
            .scalar()
        )

        if current_stock < item.quantity:
            insufficient.append(
                f"{product.name}: Available {current_stock}, Requested {item.quantity}"
            )

    if insufficient:
        raise HTTPException(
            status_code=400,
            detail="Insufficient stock:\n" + "\n".join(insufficient),
        )

    # Second pass: all validations passed, create the sale
    db_sale = Sale()
    db.add(db_sale)
    db.commit()
    db.refresh(db_sale)

    for item in sale.items:
        product = db.query(Product).filter(Product.id == item.product_id).first()

        qty = item.quantity
        sale_type = item.sale_type or "retail"

        # Auto-classify as wholesale if quantity >= 5
        if sale_type == "retail" and qty >= 5:
            sale_type = "wholesale"

        # Supply sales have no price (not a sale, just tracking inventory)
        if sale_type == "supply":
            effective_price = 0
        elif qty >= 5:
            effective_price = (product.price * qty) * 0.9
        else:
            effective_price = product.price

        db_item = SaleItem(
            sale_id=db_sale.id,
            product_id=item.product_id,
            quantity=qty,
            price=effective_price,
            sale_type=sale_type,
        )
        db.add(db_item)

    db.commit()
    # Compute total
    total = sum(item.quantity * item.price for item in db_sale.items)
    db_sale.total_price = total
    db.add(db_sale)
    db.commit()
    db.refresh(db_sale)

    return {"sale_id": db_sale.id}


@app.get("/inventory/{product_id}")
def get_inventory(
    product_id: str, db: Session = Depends(get_db), for_date: date = None
):
    if not for_date:
        for_date = date.today()

        # Fetch product
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    product_name = product.name

    # Get the previous sales day (if any)
    previous_sale = (
        db.query(SaleItem, Sale)
        .join(Sale, Sale.id == SaleItem.sale_id)
        .filter(SaleItem.product_id == product_id, Sale.timestamp < for_date)
        .order_by(Sale.timestamp.desc())
        .first()
    )

    if previous_sale:
        # Compute closing stock of previous day
        prev_date = previous_sale.Sale.timestamp.date()
        opening_stock = (
            db.query(func.coalesce(func.sum(Production.quantity), 0))
            .filter(
                Production.product_id == product_id,
                func.date(Production.timestamp) <= prev_date,
            )
            .scalar()
            - db.query(func.coalesce(func.sum(SaleItem.quantity), 0))
            .join(Sale, Sale.id == SaleItem.sale_id)
            .filter(
                SaleItem.product_id == product_id,
                func.date(Sale.timestamp) <= prev_date,
            )
            .scalar()
        )
    else:
        # No previous sales day → opening stock = 0
        opening_stock = 0

    # Production today
    production_stock = (
        db.query(func.coalesce(func.sum(Production.quantity), 0))
        .filter(
            Production.product_id == product_id,
            func.date(Production.timestamp) == for_date,
        )
        .scalar()
    )

    # Sales today
    sales_stock = (
        db.query(func.coalesce(func.sum(SaleItem.quantity), 0))
        .join(Sale, Sale.id == SaleItem.sale_id)
        .filter(
            SaleItem.product_id == product_id, func.date(Sale.timestamp) == for_date
        )
        .scalar()
    )

    # Closing stock today
    closing_stock = (opening_stock or 0) + (production_stock or 0) - (sales_stock or 0)

    # Current stock (up to now)
    current_stock = (
        db.query(func.coalesce(func.sum(Production.quantity), 0))
        .filter(Production.product_id == product_id)
        .scalar()
        - db.query(func.coalesce(func.sum(SaleItem.quantity), 0))
        .filter(SaleItem.product_id == product_id)
        .scalar()
    )

    return {
        "product_id": product_id,
        "product_name": product_name,
        "opening_stock": 0 if opening_stock < 0 else opening_stock,
        "production_stock": 0 if production_stock < 0 else production_stock,
        "sales_stock": 0 if sales_stock < 0 else sales_stock,
        "closing_stock": 0 if closing_stock < 0 else closing_stock,
        "current_stock": 0 if current_stock < 0 else current_stock,
    }
