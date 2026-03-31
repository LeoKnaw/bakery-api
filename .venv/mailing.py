from fastapi.params import Depends
from sqlalchemy import func
from datetime import date, timedelta
from models import Product, Sale, SaleItem, Production
from database import get_db
from fastapi import FastAPI, HTTPException, Depends
import smtplib
import os
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
        # Previous day closing stock
        prev_day = report_date - timedelta(days=1)
        previous_production = (
            db.query(func.coalesce(func.sum(Production.quantity), 0))
            .filter(
                Production.product_id == product.id, Production.timestamp <= prev_day
            )
            .scalar()
        )
        previous_sales_qty = (
            db.query(func.coalesce(func.sum(SaleItem.quantity), 0))
            .join(Sale, Sale.id == SaleItem.sale_id)
            .filter(SaleItem.product_id == product.id, Sale.timestamp <= prev_day)
            .scalar()
        )
        opening_stock = max(previous_production - previous_sales_qty, 0)

        # Production today
        production_today = (
            db.query(func.coalesce(func.sum(Production.quantity), 0))
            .filter(
                Production.product_id == product.id,
                func.date(Production.timestamp) == report_date,
            )
            .scalar()
        )

        # Sales today
        sales_today_qty = (
            db.query(func.coalesce(func.sum(SaleItem.quantity), 0))
            .join(Sale, Sale.id == SaleItem.sale_id)
            .filter(
                SaleItem.product_id == product.id,
                func.date(Sale.timestamp) == report_date,
            )
            .scalar()
        )

        # Total sales amount today
        total_sales_amount = (
            db.query(func.coalesce(func.sum(SaleItem.quantity * SaleItem.price), 0))
            .join(Sale, Sale.id == SaleItem.sale_id)
            .filter(
                SaleItem.product_id == product.id,
                func.date(Sale.timestamp) == report_date,
            )
            .scalar()
        )

        closing_stock = opening_stock + (production_today or 0) - (sales_today_qty or 0)

        report_rows.append(
            {
                "product_name": product.name,
                "opening_stock": opening_stock or 0,
                "production": production_today or 0,
                "sales_qty": sales_today_qty or 0,
                "total_sales": total_sales_amount or 0,  # ✅ new field
                "closing_stock": closing_stock or 0,
            }
        )

    return report_rows


def format_report_html(report, report_date):
    report_rows = report["rows"]
    totals = report["totals"]

    html = f"<h2>Bakery Daily Report: {report_date}</h2>"
    html += "<table border='1' cellpadding='5' cellspacing='0'>"
    html += "<tr><th>Product</th><th>Opening Stock</th><th>Production</th><th>Sales Qty</th><th>Total Sales</th><th>Closing Stock</th></tr>"

    for row in report_rows:
        html += f"<tr><td>{row['product_name']}</td><td>{row['opening_stock']}</td><td>{row['production']}</td><td>{row['sales_qty']}</td><td>{row['total_sales']}</td><td>{row['closing_stock']}</td></tr>"

    html += "</table>"
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
    send_daily_email(html)
