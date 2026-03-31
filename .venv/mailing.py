from fastapi.params import Depends
from sqlalchemy import func
from datetime import date, timedelta
from models import Product, Sale, SaleItem, Production
from database import get_db
from fastapi import FastAPI, HTTPException, Depends
import smtplib
import os
import api_client
from dotenv import load_dotenv
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

load_dotenv()


EMAIL_ADDRESS = os.getenv("EMAIL_ADDRESS")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")
REPORT_RECIPIENT = os.getenv("REPORT_RECIPIENT")


def get_daily_report(db, report_date: date = None):
    if not report_date:
        report_date = date.today()

    report_rows = []

    products = db.query(Product).all()

    for product in products:
        # Get opening stock and production from API
        inventory = api_client.get_inventory(
            str(product.id), for_date=report_date.isoformat()
        )
        opening_stock = inventory["opening_stock"]
        production_today = inventory["production_stock"]

        # Wholesale sales today (quantity >= 5)
        wholesale_qty = (
            db.query(func.coalesce(func.sum(SaleItem.quantity), 0))
            .join(Sale, Sale.id == SaleItem.sale_id)
            .filter(
                SaleItem.product_id == product.id,
                func.date(Sale.timestamp) == report_date,
                SaleItem.quantity >= 5,
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
            )
            .scalar()
        )

        # Retail sales today (quantity < 5)
        retail_qty = (
            db.query(func.coalesce(func.sum(SaleItem.quantity), 0))
            .join(Sale, Sale.id == SaleItem.sale_id)
            .filter(
                SaleItem.product_id == product.id,
                func.date(Sale.timestamp) == report_date,
                SaleItem.quantity < 5,
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
            )
            .scalar()
        )

        # Total sales qty
        sales_today_qty = (wholesale_qty or 0) + (retail_qty or 0)

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
                "closing_stock": closing_stock or 0,
            }
        )

    # Calculate totals
    totals = {
        "wholesale_qty": sum(r["wholesale_qty"] for r in report_rows),
        "wholesale_revenue": sum(r["wholesale_revenue"] for r in report_rows),
        "retail_qty": sum(r["retail_qty"] for r in report_rows),
        "retail_revenue": sum(r["retail_revenue"] for r in report_rows),
    }
    totals["daily_revenue"] = totals["wholesale_revenue"] + totals["retail_revenue"]

    return {"rows": report_rows, "totals": totals}


def format_report_html(report, report_date):
    report_rows = report["rows"]
    totals = report["totals"]

    html = f"<h2>Bakery Daily Report: {report_date}</h2>"
    html += "<table border='1' cellpadding='5' cellspacing='0'>"
    html += "<tr><th>Product</th><th>Opening Stock</th><th>Production</th><th>Wholesale Qty</th><th>Wholesale Revenue</th><th>Retail Qty</th><th>Retail Revenue</th><th>Closing Stock</th></tr>"

    for row in report_rows:
        html += f"<tr><td>{row['product_name']}</td><td>{row['opening_stock']}</td><td>{row['production']}</td><td>{row['wholesale_qty']}</td><td>{row['wholesale_revenue']}</td><td>{row['retail_qty']}</td><td>{row['retail_revenue']}</td><td>{row['closing_stock']}</td></tr>"

    # Totals row
    html += f"<tr style='font-weight:bold;'><td>Total</td><td></td><td></td><td>{totals['wholesale_qty']}</td><td>{totals['wholesale_revenue']}</td><td>{totals['retail_qty']}</td><td>{totals['retail_revenue']}</td><td></td></tr>"

    html += "</table>"

    # Summary below table
    html += f"<p><strong>Total Daily Revenue: {totals['daily_revenue']}</strong> (Wholesale: {totals['wholesale_revenue']} + Retail: {totals['retail_revenue']})</p>"

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
    db = next(get_db())
    report = get_daily_report(db, report_date=date.today())
    db.close()

    html = format_report_html(report, report_date=date.today())
    print(html)  # Preview before sending
    send_daily_email(html)
