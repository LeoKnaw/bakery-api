from fastapi import FastAPI, HTTPException, Depends, Header
from fastapi.middleware.cors import CORSMiddleware
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
    UserRegister,
    UserLogin,
    UserResponse,
    LoginResponse,
    DailyStockRecordCreate,
    DailyStockRecordUpdate,
    DailyStockRecordResponse,
    DailyStockRecordWithProduct,
)
from models import Base, Product, Production, Sale, SaleItem, User, DailyStockRecord
from database import Base, engine, SessionLocal, API_KEY
from uuid import uuid4, UUID
from sqlalchemy import func
from sqlalchemy.orm import Session
from datetime import datetime, date
import bcrypt
import secrets

app = FastAPI()

# CORS middleware - restrict access to your Streamlit app
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:8501",
        "http://127.0.0.1:8501",
        "https://*.onrender.com",
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH"],
    allow_headers=["*"],
)

Base.metadata.create_all(bind=engine)


# Password hashing using bcrypt directly
def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(
        plain_password.encode("utf-8"), hashed_password.encode("utf-8")
    )


def create_token() -> str:
    return secrets.token_urlsafe(32)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# API Key authentication dependency (for API access)
def verify_api_key(x_api_key: Optional[str] = Header(None)):
    """Verify API key for protected endpoints. GET requests are public."""
    if x_api_key != API_KEY:
        raise HTTPException(status_code=401, detail="Invalid or missing API Key")


# User authentication dependency (for web users)
def get_current_user(
    x_token: Optional[str] = Header(None), db: Session = Depends(get_db)
):
    """Get current user from token header."""
    if not x_token:
        raise HTTPException(status_code=401, detail="Missing authentication token")

    # Token format: user_id:token_string
    try:
        user_id_str, token = x_token.split(":")
        user_id = UUID(user_id_str)
    except (ValueError, AttributeError):
        raise HTTPException(status_code=401, detail="Invalid token format")

    user = db.query(User).filter(User.id == user_id).first()
    if not user or user.password_hash != token:
        raise HTTPException(status_code=401, detail="Invalid token")

    if not user.is_approved:
        raise HTTPException(status_code=403, detail="Account pending approval")

    return user


def get_admin_user(user: User = Depends(get_current_user)):
    """Dependency that requires admin privileges."""
    if not user.is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")
    return user


@app.get("/")
async def root():
    return {"status": "ok", "name": "Fadel Bakery"}


@app.get("/fadel/products", response_model=List[ProductResponse])
async def get_products(db: Session = Depends(get_db)):
    return db.query(Product).filter(Product.is_active == True).all()


@app.post(
    "/fadel/products",
    response_model=ProductResponse,
    dependencies=[Depends(verify_api_key)],
)
async def create_product(product: ProductCreate, db: Session = Depends(get_db)):
    db_product = Product(name=product.name, price=product.price)
    db.add(db_product)
    db.commit()
    db.refresh(db_product)
    return db_product


@app.put(
    "/fadel/products/{product_id}",
    response_model=ProductResponse,
    dependencies=[Depends(verify_api_key)],
)
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


@app.patch(
    "/fadel/products/{product_id}/deactivate", dependencies=[Depends(verify_api_key)]
)
async def deactivate_product(product_id: UUID, db: Session = Depends(get_db)):
    product = db.query(Product).filter(Product.id == product_id).first()

    if not product:
        raise HTTPException(status_code=404, detail=f"Product {product_id} not found")

    product.is_active = False
    db.commit()
    db.refresh(product)
    return product


# Production and inventory endpoints


# creating a new product. like baking a bread
@app.post(
    "/fadel/production",
    response_model=ProductionRecord,
    dependencies=[Depends(verify_api_key)],
)
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


@app.post("/sales", dependencies=[Depends(verify_api_key)])
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
        elif sale_type == "wholesale" or qty >= 5:
            effective_price = product.price * 0.9  # 10% off per unit
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


# ==================== AUTH ENDPOINTS ====================


@app.post("/auth/register", response_model=UserResponse)
async def register(user: UserRegister, db: Session = Depends(get_db)):
    """Register a new user (pending approval)."""
    # Check if username exists
    existing = db.query(User).filter(User.username == user.username).first()
    if existing:
        raise HTTPException(status_code=400, detail="Username already exists")

    # Check if this is the first user (auto-approve and make admin)
    user_count = db.query(User).count()
    is_first_user = user_count == 0

    new_user = User(
        username=user.username,
        password_hash=hash_password(user.password),
        is_approved=is_first_user,  # Auto-approve first user
        is_admin=is_first_user,  # First user is admin
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user


@app.post("/auth/login", response_model=LoginResponse)
async def login(user: UserLogin, db: Session = Depends(get_db)):
    """Login and get access token."""
    db_user = db.query(User).filter(User.username == user.username).first()

    if not db_user or not verify_password(user.password, db_user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid username or password")

    if not db_user.is_approved:
        raise HTTPException(
            status_code=403, detail="Account pending approval. Contact admin."
        )

    # Return token as user_id:token_hash
    token = f"{db_user.id}:{db_user.password_hash}"

    return LoginResponse(
        access_token=token,
        is_admin=db_user.is_admin,
        is_approved=db_user.is_approved,
    )


@app.get("/auth/pending", response_model=List[UserResponse])
async def get_pending_users(
    user: User = Depends(get_admin_user), db: Session = Depends(get_db)
):
    """Get all pending users (admin only)."""
    return db.query(User).filter(User.is_approved == False).all()


@app.post("/auth/approve/{user_id}", response_model=UserResponse)
async def approve_user(
    user_id: UUID, user: User = Depends(get_admin_user), db: Session = Depends(get_db)
):
    """Approve a pending user (admin only)."""
    pending_user = db.query(User).filter(User.id == user_id).first()
    if not pending_user:
        raise HTTPException(status_code=404, detail="User not found")

    pending_user.is_approved = True
    db.commit()
    db.refresh(pending_user)
    return pending_user


@app.get("/auth/users", response_model=List[UserResponse])
async def get_all_users(
    user: User = Depends(get_admin_user), db: Session = Depends(get_db)
):
    """Get all users (admin only)."""
    return db.query(User).all()


# ==================== DAILY STOCK RECORD ENDPOINTS ====================


def calculate_closing_stock(
    opening: int, production: int, wholesale: int, retail: int
) -> int:
    """Calculate closing stock from components."""
    return opening + production - wholesale - retail


@app.post("/stock/daily", response_model=List[DailyStockRecordWithProduct])
async def create_daily_stock_records(
    record_date: date,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Create daily stock records for all active products."""
    existing = (
        db.query(DailyStockRecord)
        .filter(DailyStockRecord.record_date == record_date)
        .first()
    )
    if existing:
        raise HTTPException(
            status_code=400,
            detail=f"Daily stock records for {record_date} already exist. Use PUT to update.",
        )

    products = db.query(Product).filter(Product.is_active == True).all()
    if not products:
        raise HTTPException(status_code=404, detail="No active products found")

    records = []
    for product in products:
        record = DailyStockRecord(
            record_date=record_date,
            product_id=product.id,
            opening_stock=0,
            production_stock=0,
            wholesale_quantity=0,
            retail_quantity=0,
            wholesale_revenue=0.0,
            retail_revenue=0.0,
            closing_stock=0,
        )
        db.add(record)
        records.append(record)

    db.commit()
    for record in records:
        db.refresh(record)
        record.product = (
            db.query(Product).filter(Product.id == record.product_id).first()
        )

    return records


@app.get("/stock/daily", response_model=List[DailyStockRecordWithProduct])
async def get_daily_stock_records(
    record_date: Optional[date] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    product_id: Optional[str] = None,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Get daily stock records with filtering options."""
    query = db.query(DailyStockRecord)

    if record_date:
        query = query.filter(DailyStockRecord.record_date == record_date)
    elif start_date and end_date:
        query = query.filter(
            DailyStockRecord.record_date >= start_date,
            DailyStockRecord.record_date <= end_date,
        )
    elif start_date:
        query = query.filter(DailyStockRecord.record_date >= start_date)
    elif end_date:
        query = query.filter(DailyStockRecord.record_date <= end_date)

    if product_id:
        query = query.filter(DailyStockRecord.product_id == product_id)

    records = query.order_by(DailyStockRecord.record_date.desc()).all()

    for record in records:
        record.product = (
            db.query(Product).filter(Product.id == record.product_id).first()
        )

    return records


@app.get("/stock/daily/{record_id}", response_model=DailyStockRecordWithProduct)
async def get_daily_stock_record(
    record_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Get a single daily stock record by ID."""
    record = db.query(DailyStockRecord).filter(DailyStockRecord.id == record_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="Stock record not found")

    record.product = db.query(Product).filter(Product.id == record.product_id).first()
    return record


@app.put("/stock/daily/{record_id}", response_model=DailyStockRecordResponse)
async def update_daily_stock_record(
    record_id: UUID,
    update: DailyStockRecordUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Update a daily stock record. Recalculates closing stock automatically."""
    record = db.query(DailyStockRecord).filter(DailyStockRecord.id == record_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="Stock record not found")

    if update.opening_stock is not None:
        record.opening_stock = update.opening_stock
    if update.production_stock is not None:
        record.production_stock = update.production_stock
    if update.wholesale_quantity is not None:
        record.wholesale_quantity = update.wholesale_quantity
    if update.retail_quantity is not None:
        record.retail_quantity = update.retail_quantity
    if update.wholesale_revenue is not None:
        record.wholesale_revenue = update.wholesale_revenue
    if update.retail_revenue is not None:
        record.retail_revenue = update.retail_revenue

    record.closing_stock = calculate_closing_stock(
        record.opening_stock,
        record.production_stock,
        record.wholesale_quantity,
        record.retail_quantity,
    )

    db.commit()
    db.refresh(record)
    return record


@app.get("/stock/summary")
async def get_stock_summary(
    start_date: date,
    end_date: date,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Get summary of stock records for a date range."""
    records = (
        db.query(DailyStockRecord)
        .filter(
            DailyStockRecord.record_date >= start_date,
            DailyStockRecord.record_date <= end_date,
        )
        .all()
    )

    total_opening = sum(r.opening_stock for r in records)
    total_production = sum(r.production_stock for r in records)
    total_wholesale_qty = sum(r.wholesale_quantity for r in records)
    total_retail_qty = sum(r.retail_quantity for r in records)
    total_wholesale_rev = sum(r.wholesale_revenue for r in records)
    total_retail_rev = sum(r.retail_revenue for r in records)
    total_closing = sum(r.closing_stock for r in records)

    product_summary = {}
    for record in records:
        pid = str(record.product_id)
        if pid not in product_summary:
            product = db.query(Product).filter(Product.id == record.product_id).first()
            product_summary[pid] = {
                "product_id": pid,
                "product_name": product.name if product else "Unknown",
                "total_production": 0,
                "total_wholesale": 0,
                "total_retail": 0,
                "total_revenue": 0,
            }
        product_summary[pid]["total_production"] += record.production_stock
        product_summary[pid]["total_wholesale"] += record.wholesale_quantity
        product_summary[pid]["total_retail"] += record.retail_quantity
        product_summary[pid]["total_revenue"] += (
            record.wholesale_revenue + record.retail_revenue
        )

    return {
        "start_date": start_date,
        "end_date": end_date,
        "total_records": len(records),
        "totals": {
            "opening_stock": total_opening,
            "production_stock": total_production,
            "wholesale_quantity": total_wholesale_qty,
            "retail_quantity": total_retail_qty,
            "wholesale_revenue": total_wholesale_rev,
            "retail_revenue": total_retail_rev,
            "closing_stock": total_closing,
            "total_revenue": total_wholesale_rev + total_retail_rev,
        },
        "by_product": list(product_summary.values()),
    }
