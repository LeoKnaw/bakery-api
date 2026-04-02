from sqlalchemy import func
from sqlalchemy.orm import Session
from datetime import date
from models import Product, Sale, SaleItem, Production
from database import SessionLocal
import smtplib
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

EMAIL_ADDRESS = os.getenv("EMAIL_ADDRESS")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")
REPORT_RECIPIENT = os.getenv("REPORT_RECIPIENT")


def get_inventory_data(db: Session, product_id, for_date: date):
    """Calculate inventory data directly from database (no API call needed)."""
    # Get the previous sales day (if any)
    previous_sale = (
        db.query(SaleItem, Sale)
        .join(Sale, Sale.id == SaleItem.sale_id)
        .filter(SaleItem.product_id == product_id, Sale.timestamp < for_date)
        .order_by(Sale.timestamp.desc())
        .first()
    )

    if previous_sale:
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
        opening_stock = 0

    # Production today
    production_today = (
        db.query(func.coalesce(func.sum(Production.quantity), 0))
        .filter(
            Production.product_id == product_id,
            func.date(Production.timestamp) == for_date,
        )
        .scalar()
    )

    return {
        "opening_stock": 0 if (opening_stock or 0) < 0 else (opening_stock or 0),
        "production_stock": 0
        if (production_today or 0) < 0
        else (production_today or 0),
    }


def get_daily_report(db: Session, report_date: date = None):
    if not report_date:
        report_date = date.today()

    report_rows = []

    products = db.query(Product).all()

    for product in products:
        # Get opening stock and production from database directly
        inventory = get_inventory_data(db, product.id, report_date)
        opening_stock = inventory["opening_stock"]
        production_today = inventory["production_stock"]

        # Wholesale sales today (quantity >= 5, not supply)
        wholesale_qty = (
            db.query(func.coalesce(func.sum(SaleItem.quantity), 0))
            .join(Sale, Sale.id == SaleItem.sale_id)
            .filter(
                SaleItem.product_id == product.id,
                func.date(Sale.timestamp) == report_date,
                SaleItem.quantity >= 5,
                SaleItem.sale_type != "supply",
            )
            .scalar()
        )
        wholesale_revenue = (
            db.query(func.coalesce(func.sum(SaleItem.quantity * SaleItem.price), 0))
            .join(Sale, Sale.id == SaleItem.sale_id)
            .filter(
                SaleItem.product_id == product.id,
                func.date(Sale.timestamp) == report_date,
                SaleItem.quantity >= 5,
                SaleItem.sale_type != "supply",
            )
            .scalar()
        )

        # Retail sales today (quantity < 5, not supply)
        retail_qty = (
            db.query(func.coalesce(func.sum(SaleItem.quantity), 0))
            .join(Sale, Sale.id == SaleItem.sale_id)
            .filter(
                SaleItem.product_id == product.id,
                func.date(Sale.timestamp) == report_date,
                SaleItem.quantity < 5,
                SaleItem.sale_type != "supply",
            )
            .scalar()
        )
        retail_revenue = (
            db.query(func.coalesce(func.sum(SaleItem.quantity * SaleItem.price), 0))
            .join(Sale, Sale.id == SaleItem.sale_id)
            .filter(
                SaleItem.product_id == product.id,
                func.date(Sale.timestamp) == report_date,
                SaleItem.quantity < 5,
                SaleItem.sale_type != "supply",
            )
            .scalar()
        )

        # Supply sales today
        supply_qty = (
            db.query(func.coalesce(func.sum(SaleItem.quantity), 0))
            .join(Sale, Sale.id == SaleItem.sale_id)
            .filter(
                SaleItem.product_id == product.id,
                func.date(Sale.timestamp) == report_date,
                SaleItem.sale_type == "supply",
            )
            .scalar()
        )

        # Total sales qty (exclude supply from sales, include in stock reduction)
        sales_today_qty = (wholesale_qty or 0) + (retail_qty or 0) + (supply_qty or 0)

        closing_stock = opening_stock + (production_today or 0) - (sales_today_qty or 0)

        report_rows.append(
            {
                "product_name": product.name,
                "opening_stock": opening_stock or 0,
                "production": production_today or 0,
                "wholesale_qty": wholesale_qty or 0,
                "wholesale_revenue": wholesale_revenue or 0,
                "retail_qty": retail_qty or 0,
                "retail_revenue": retail_revenue or 0,
                "supply_qty": supply_qty or 0,
                "closing_stock": closing_stock or 0,
            }
        )

    # Calculate totals
    totals = {
        "wholesale_qty": sum(r["wholesale_qty"] for r in report_rows),
        "wholesale_revenue": sum(r["wholesale_revenue"] for r in report_rows),
        "retail_qty": sum(r["retail_qty"] for r in report_rows),
        "retail_revenue": sum(r["retail_revenue"] for r in report_rows),
        "supply_qty": sum(r["supply_qty"] for r in report_rows),
    }
    totals["daily_revenue"] = totals["wholesale_revenue"] + totals["retail_revenue"]

    return {"rows": report_rows, "totals": totals}


def format_report_html(report, report_date):
    report_rows = report["rows"]
    totals = report["totals"]

    html = f"<h2>Bakery Daily Report: {report_date}</h2>"
    html += "<table border='1' cellpadding='5' cellspacing='0'>"
    html += "<tr><th>Product</th><th>Opening Stock</th><th>Production</th><th>Wholesale Qty</th><th>Wholesale Revenue</th><th>Retail Qty</th><th>Retail Revenue</th><th>Supply Qty</th><th>Closing Stock</th></tr>"

    for row in report_rows:
        html += f"<tr><td>{row['product_name']}</td><td>{row['opening_stock']}</td><td>{row['production']}</td><td>{row['wholesale_qty']}</td><td>{row['wholesale_revenue']}</td><td>{row['retail_qty']}</td><td>{row['retail_revenue']}</td><td>{row['supply_qty']}</td><td>{row['closing_stock']}</td></tr>"

    # Totals row
    html += f"<tr style='font-weight:bold;'><td>Total</td><td></td><td></td><td>{totals['wholesale_qty']}</td><td>{totals['wholesale_revenue']}</td><td>{totals['retail_qty']}</td><td>{totals['retail_revenue']}</td><td>{totals['supply_qty']}</td><td></td></tr>"

    html += "</table>"

    # Summary below table
    html += f"<p><strong>Total Daily Revenue: {totals['daily_revenue']}</strong> (Wholesale: {totals['wholesale_revenue']} + Retail: {totals['retail_revenue']})</p>"
    html += f"<p><strong>Total Supply:</strong> {totals['supply_qty']} units</p>"

    return html


def send_daily_email(report_html, to_email=REPORT_RECIPIENT):
    msg = MIMEMultipart()
    msg["From"] = EMAIL_ADDRESS
    msg["To"] = to_email
    msg["Subject"] = "Bakery Daily Report"

    msg.attach(MIMEText(report_html, "html"))

    with smtplib.SMTP("smtp.gmail.com", 587) as server:
        server.starttls()
        server.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
        server.send_message(msg)


if __name__ == "__main__":
    print(f"Generating daily report for {date.today()}...")

    # Create database session directly (no FastAPI dependency)
    db = SessionLocal()
    try:
        report = get_daily_report(db, report_date=date.today())

        html = format_report_html(report, report_date=date.today())
        print("Report generated. Sending email...")

        send_daily_email(html)

        print(f"Email sent successfully to {REPORT_RECIPIENT}")
    except Exception as e:
        print(f"Error: {e}")
        raise
    finally:
        db.close()
