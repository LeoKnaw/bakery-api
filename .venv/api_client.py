"""
API client for communicating with the bakery FastAPI backend.
"""

import requests
import os
from typing import Optional
from dotenv import load_dotenv

current_dir = os.path.dirname(os.path.abspath(__file__))
dotenv_path = os.path.join(current_dir, ".env")
load_dotenv(dotenv_path=dotenv_path)

BASE_URL = os.getenv("BASE_URL", "http://localhost:8000")
API_KEY = os.getenv("API_KEY", "bakery-secret-key-2026")

# Headers with API key for authenticated requests
HEADERS = {"X-API-Key": API_KEY}

# User token storage (for session management)
_USER_TOKEN = None
_USER_IS_ADMIN = False


def set_user_token(token: str, is_admin: bool):
    """Store user token after login."""
    global _USER_TOKEN, _USER_IS_ADMIN
    _USER_TOKEN = token
    _USER_IS_ADMIN = is_admin


def get_user_headers() -> dict:
    """Get headers with user token for authenticated requests."""
    if _USER_TOKEN:
        return {"X-Token": _USER_TOKEN}
    return {}


def is_admin() -> bool:
    """Check if current user is admin."""
    return _USER_IS_ADMIN


def is_logged_in() -> bool:
    """Check if user is logged in."""
    return _USER_TOKEN is not None


def logout():
    """Clear user session."""
    global _USER_TOKEN, _USER_IS_ADMIN
    _USER_TOKEN = None
    _USER_IS_ADMIN = False


# ==================== AUTH FUNCTIONS ====================


def register(username: str, password: str) -> dict:
    """Register a new user."""
    response = requests.post(
        f"{BASE_URL}/auth/register",
        json={"username": username, "password": password},
    )
    if not response.ok:
        error_detail = response.json().get("detail", "Registration failed")
        raise ValueError(error_detail)
    return response.json()


def login(username: str, password: str) -> dict:
    """Login and get access token."""
    response = requests.post(
        f"{BASE_URL}/auth/login",
        json={"username": username, "password": password},
    )
    if not response.ok:
        error_detail = response.json().get("detail", "Login failed")
        raise ValueError(error_detail)
    data = response.json()
    set_user_token(data["access_token"], data["is_admin"])
    return data


def get_pending_users() -> list:
    """Get pending users (admin only)."""
    response = requests.get(
        f"{BASE_URL}/auth/pending",
        headers=get_user_headers(),
    )
    response.raise_for_status()
    return response.json()


def approve_user(user_id: str) -> dict:
    """Approve a pending user (admin only)."""
    response = requests.post(
        f"{BASE_URL}/auth/approve/{user_id}",
        headers=get_user_headers(),
    )
    response.raise_for_status()
    return response.json()


def get_all_users() -> list:
    """Get all users (admin only)."""
    response = requests.get(
        f"{BASE_URL}/auth/users",
        headers=get_user_headers(),
    )
    response.raise_for_status()
    return response.json()


def get_products() -> list:
    """Fetch all products from the API."""
    response = requests.get(f"{BASE_URL}/fadel/products")
    response.raise_for_status()
    return response.json()


def create_product(name: str, price: float, wholesale_price: float) -> dict:
    """Create a new product."""
    response = requests.post(
        f"{BASE_URL}/fadel/products",
        json={"name": name, "price": price, "wholesale_price": wholesale_price},
        headers=HEADERS,
    )
    response.raise_for_status()
    return response.json()


def update_product(
    product_id: str, name: Optional[str] = None, price: Optional[float] = None, wholesale_price: Optional[float] = None
) -> dict:
    """Update an existing product."""
    payload = {}
    if name is not None:
        payload["name"] = name
    if price is not None:
        payload["price"] = price
    if wholesale_price is not None:
        payload["wholesale_price"] = wholesale_price

    response = requests.put(
        f"{BASE_URL}/fadel/products/{product_id}",
        json=payload,
        headers=HEADERS,
    )
    response.raise_for_status()
    return response.json()


def deactivate_product(product_id: str) -> dict:
    """Deactivate a product (soft delete)."""
    response = requests.patch(
        f"{BASE_URL}/fadel/products/{product_id}/deactivate",
        headers=HEADERS,
    )
    response.raise_for_status()
    return response.json()


# Keep old function for backwards compatibility
def delete_product(product_id: str) -> dict:
    """Deactivate a product (soft delete)."""
    return deactivate_product(product_id)


def record_production(product_id: str, quantity: int) -> dict:
    """Record a production batch (baking)."""
    response = requests.post(
        f"{BASE_URL}/fadel/production",
        json={"product_id": product_id, "quantity": quantity},
        headers=HEADERS,
    )
    response.raise_for_status()
    return response.json()


def get_production_records() -> list:
    """Fetch all production records."""
    response = requests.get(f"{BASE_URL}/fadel/production")
    response.raise_for_status()
    return response.json()


def create_sale(items: list[dict]) -> dict:
    """
    Create a sale with multiple items.

    items: list of {"product_id": str, "quantity": int, "sale_type": str}
    """
    try:
        response = requests.post(
            f"{BASE_URL}/sales",
            json={"items": items},
            headers=HEADERS,
        )
        response.raise_for_status()
        return response.json()
    except requests.exceptions.HTTPError as e:
        try:
            error_detail = e.response.json().get("detail", str(e))
        except Exception:
            error_detail = str(e)
        raise ValueError(error_detail)


def get_inventory(product_id: str, for_date: Optional[str] = None) -> dict:
    """
    Get inventory for a product.

    for_date: optional date string in YYYY-MM-DD format
    """
    params = {}
    if for_date:
        params["for_date"] = for_date

    response = requests.get(f"{BASE_URL}/inventory/{product_id}", params=params)
    response.raise_for_status()
    return response.json()


# ==================== DAILY STOCK RECORD FUNCTIONS ====================


def create_daily_stock_records(record_date: str) -> list:
    """Create daily stock records for all active products."""
    response = requests.post(
        f"{BASE_URL}/stock/daily?record_date={record_date}",
        headers=get_user_headers(),
    )
    if not response.ok:
        error_detail = response.json().get("detail", "Failed to create daily records")
        raise ValueError(error_detail)
    return response.json()


def get_daily_stock_records(
    record_date: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    product_id: Optional[str] = None,
) -> list:
    """Get daily stock records with optional filters."""
    params = {}
    if record_date:
        params["record_date"] = record_date
    if start_date:
        params["start_date"] = start_date
    if end_date:
        params["end_date"] = end_date
    if product_id:
        params["product_id"] = product_id

    response = requests.get(
        f"{BASE_URL}/stock/daily",
        params=params,
        headers=get_user_headers(),
    )
    response.raise_for_status()
    return response.json()


def get_daily_stock_record(record_id: str) -> dict:
    """Get a single daily stock record by ID."""
    response = requests.get(
        f"{BASE_URL}/stock/daily/{record_id}",
        headers=get_user_headers(),
    )
    response.raise_for_status()
    return response.json()


def update_daily_stock_record(
    record_id: str,
    opening_stock: Optional[int] = None,
    production_stock: Optional[int] = None,
    wholesale_quantity: Optional[int] = None,
    retail_quantity: Optional[int] = None,
    supply_quantity: Optional[int] = None,
    wholesale_revenue: Optional[float] = None,
    retail_revenue: Optional[float] = None,
) -> dict:
    """Update a daily stock record. Closing stock auto-calculates."""
    payload = {}
    if opening_stock is not None:
        payload["opening_stock"] = opening_stock
    if production_stock is not None:
        payload["production_stock"] = production_stock
    if wholesale_quantity is not None:
        payload["wholesale_quantity"] = wholesale_quantity
    if retail_quantity is not None:
        payload["retail_quantity"] = retail_quantity
    if supply_quantity is not None:
        payload["supply_quantity"] = supply_quantity
    if wholesale_revenue is not None:
        payload["wholesale_revenue"] = wholesale_revenue
    if retail_revenue is not None:
        payload["retail_revenue"] = retail_revenue

    response = requests.put(
        f"{BASE_URL}/stock/daily/{record_id}",
        json=payload,
        headers=get_user_headers(),
    )
    response.raise_for_status()
    return response.json()


def get_stock_summary(start_date: str, end_date: str) -> dict:
    """Get stock summary for a date range."""
    response = requests.get(
        f"{BASE_URL}/stock/summary",
        params={"start_date": start_date, "end_date": end_date},
        headers=get_user_headers(),
    )
    response.raise_for_status()
    return response.json()
