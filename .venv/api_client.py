"""
API client for communicating with the bakery FastAPI backend.
"""

import requests
from typing import Optional

BASE_URL = "http://localhost:8000"


def get_products() -> list:
    """Fetch all products from the API."""
    response = requests.get(f"{BASE_URL}/fadel/products")
    response.raise_for_status()
    return response.json()


def create_product(name: str, price: float) -> dict:
    """Create a new product."""
    response = requests.post(
        f"{BASE_URL}/fadel/products", json={"name": name, "price": price}
    )
    response.raise_for_status()
    return response.json()


def update_product(
    product_id: str, name: Optional[str] = None, price: Optional[float] = None
) -> dict:
    """Update an existing product."""
    payload = {}
    if name is not None:
        payload["name"] = name
    if price is not None:
        payload["price"] = price

    response = requests.put(f"{BASE_URL}/fadel/products/{product_id}", json=payload)
    response.raise_for_status()
    return response.json()


def delete_product(product_id: str) -> None:
    """Delete a product."""
    response = requests.delete(f"{BASE_URL}/fadel/delete/{product_id}")
    response.raise_for_status()


def record_production(product_id: str, quantity: int) -> dict:
    """Record a production batch (baking)."""
    response = requests.post(
        f"{BASE_URL}/fadel/production",
        json={"product_id": product_id, "quantity": quantity},
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
        response = requests.post(f"{BASE_URL}/sales", json={"items": items})
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
