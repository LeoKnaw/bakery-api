from fastapi import FastAPI, HTTPException, Depends
from typing import Optional, List
from schema import (
    DailyStockRecordUpdate,
    DailyStockRecordResponse,
    DailyStockRecordWithProduct,
)
from models import Product, DailyStockRecord, User
from database import SessionLocal
from uuid import UUID
from datetime import date


def calculate_closing_stock(
    opening: int, production: int, wholesale: int, retail: int, supply: int = 0
) -> int:
    """Calculate closing stock from components."""
    return opening + production - wholesale - retail - supply


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_current_user_dependency():
    """This will be imported from bakery.py main app"""
    pass


def get_admin_user_dependency():
    """This will be imported from bakery.py main app"""
    pass


def create_stock_routes(app: FastAPI, get_current_user, get_admin_user):
    """Add daily stock record routes to the FastAPI app."""

    @app.post("/stock/daily", response_model=List[DailyStockRecordWithProduct])
    async def create_daily_stock_records(
        record_date: date,
        db=Depends(get_db),
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
                supply_quantity=0,
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
        db=Depends(get_db),
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
        db=Depends(get_db),
        user: User = Depends(get_current_user),
    ):
        """Get a single daily stock record by ID."""
        record = (
            db.query(DailyStockRecord).filter(DailyStockRecord.id == record_id).first()
        )
        if not record:
            raise HTTPException(status_code=404, detail="Stock record not found")

        record.product = (
            db.query(Product).filter(Product.id == record.product_id).first()
        )
        return record

    @app.put("/stock/daily/{record_id}", response_model=DailyStockRecordResponse)
    async def update_daily_stock_record(
        record_id: UUID,
        update: DailyStockRecordUpdate,
        db=Depends(get_db),
        user: User = Depends(get_current_user),
    ):
        """Update a daily stock record. Recalculates closing stock automatically."""
        record = (
            db.query(DailyStockRecord).filter(DailyStockRecord.id == record_id).first()
        )
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
        if update.supply_quantity is not None:
            record.supply_quantity = update.supply_quantity
        if update.wholesale_revenue is not None:
            record.wholesale_revenue = update.wholesale_revenue
        if update.retail_revenue is not None:
            record.retail_revenue = update.retail_revenue

        record.closing_stock = calculate_closing_stock(
            record.opening_stock,
            record.production_stock,
            record.wholesale_quantity,
            record.retail_quantity,
            record.supply_quantity
        )

        db.commit()
        db.refresh(record)
        return record

    @app.get("/stock/summary")
    async def get_stock_summary(
        start_date: date,
        end_date: date,
        db=Depends(get_db),
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
        total_supply_qty = sum(r.supply_quantity for r in records)
        total_wholesale_rev = sum(r.wholesale_revenue for r in records)
        total_retail_rev = sum(r.retail_revenue for r in records)
        total_closing = sum(r.closing_stock for r in records)

        product_summary = {}
        for record in records:
            pid = str(record.product_id)
            if pid not in product_summary:
                product = (
                    db.query(Product).filter(Product.id == record.product_id).first()
                )
                product_summary[pid] = {
                    "product_id": pid,
                    "product_name": product.name if product else "Unknown",
                    "total_production": 0,
                    "total_wholesale": 0,
                    "total_retail": 0,
                    "total_supply": 0,
                    "total_revenue": 0,
                }
            product_summary[pid]["total_production"] += record.production_stock
            product_summary[pid]["total_wholesale"] += record.wholesale_quantity
            product_summary[pid]["total_retail"] += record.retail_quantity
            product_summary[pid]["total_supply"] += record.supply_quantity
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
                "supply_quantity": total_supply_qty,
                "wholesale_revenue": total_wholesale_rev,
                "retail_revenue": total_retail_rev,
                "closing_stock": total_closing,
                "total_revenue": total_wholesale_rev + total_retail_rev,
            },
            "by_product": list(product_summary.values()),
        }
