"""API tests for Bakery Management System"""

import uuid
import pytest


# Use a unique prefix for test data to avoid conflicts
TEST_PREFIX = "TEST_API_"


class TestProducts:
    """Tests for product endpoints"""

    def test_create_product(self, client, auth_headers):
        """Test creating a product returns correct data"""
        response = client.post(
            "/fadel/products",
            json={"name": f"{TEST_PREFIX}Bread", "price": 1000.0},
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == f"{TEST_PREFIX}Bread"
        assert data["price"] == 1000.0
        assert "id" in data
        assert "wholesale_price" in data
        assert data["wholesale_price"] == 900.0  # 10% discount

    def test_create_product_without_api_key(self, client):
        """Test creating a product without API key returns 401"""
        response = client.post(
            "/fadel/products",
            json={"name": f"{TEST_PREFIX}NoAuth", "price": 1000.0},
        )
        assert response.status_code == 401
        assert "API Key" in response.json()["detail"]

    def test_get_products(self, client, auth_headers):
        """Test getting all products returns a list"""
        # Create a product first
        client.post(
            "/fadel/products",
            json={"name": f"{TEST_PREFIX}Cake", "price": 500.0},
            headers=auth_headers,
        )

        response = client.get("/fadel/products")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) > 0
        # Check that our test product is in the list
        names = [p["name"] for p in data]
        assert f"{TEST_PREFIX}Cake" in names

    def test_update_product(self, client, auth_headers):
        """Test updating a product's name and price"""
        # Create a product
        create_resp = client.post(
            "/fadel/products",
            json={"name": f"{TEST_PREFIX}Croissant", "price": 700.0},
            headers=auth_headers,
        )
        product_id = create_resp.json()["id"]

        # Update the product
        response = client.put(
            f"/fadel/products/{product_id}",
            json={"name": f"{TEST_PREFIX}Croissant Updated", "price": 750.0},
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == f"{TEST_PREFIX}Croissant Updated"
        assert data["price"] == 750.0

    def test_update_nonexistent_product(self, client, auth_headers):
        """Test updating a non-existent product returns 404"""
        fake_id = str(uuid.uuid4())
        response = client.put(
            f"/fadel/products/{fake_id}",
            json={"name": "Ghost", "price": 100.0},
            headers=auth_headers,
        )
        assert response.status_code == 404


class TestProduction:
    """Tests for production endpoints"""

    def test_create_production(self, client, db_session, auth_headers):
        """Test recording production for a product"""
        # Create a product
        create_resp = client.post(
            "/fadel/products",
            json={"name": f"{TEST_PREFIX}Bread Production", "price": 1000.0},
            headers=auth_headers,
        )
        product_id = create_resp.json()["id"]

        # Record production
        response = client.post(
            "/fadel/production",
            json={"product_id": product_id, "quantity": 50},
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["quantity"] == 50
        assert data["product"]["name"] == f"{TEST_PREFIX}Bread Production"

    def test_get_production_records(self, client, db_session):
        """Test getting all production records (public endpoint)"""
        response = client.get("/fadel/production")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    def test_create_production_nonexistent_product(self, client, auth_headers):
        """Test production for non-existent product returns 404"""
        fake_id = str(uuid.uuid4())
        response = client.post(
            "/fadel/production",
            json={"product_id": fake_id, "quantity": 10},
            headers=auth_headers,
        )
        assert response.status_code == 404


class TestSales:
    """Tests for sale endpoints"""

    def test_sale_retail(self, client, db_session, auth_headers):
        """Test retail sale (qty < 5) stores unit price"""
        # Create product and production
        create_resp = client.post(
            "/fadel/products",
            json={"name": f"{TEST_PREFIX}Retail Test", "price": 1000.0},
            headers=auth_headers,
        )
        product_id = create_resp.json()["id"]

        client.post(
            "/fadel/production",
            json={"product_id": product_id, "quantity": 20},
            headers=auth_headers,
        )

        # Create retail sale (qty = 3)
        response = client.post(
            "/sales",
            json={
                "items": [
                    {"product_id": product_id, "quantity": 3, "sale_type": "retail"}
                ]
            },
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert "sale_id" in data

    def test_sale_wholesale(self, client, db_session, auth_headers):
        """Test wholesale sale (qty >= 5) applies 10% discount"""
        # Create product and production
        create_resp = client.post(
            "/fadel/products",
            json={"name": f"{TEST_PREFIX}Wholesale Test", "price": 1000.0},
            headers=auth_headers,
        )
        product_id = create_resp.json()["id"]

        client.post(
            "/fadel/production",
            json={"product_id": product_id, "quantity": 20},
            headers=auth_headers,
        )

        # Create wholesale sale (qty = 7)
        response = client.post(
            "/sales",
            json={"items": [{"product_id": product_id, "quantity": 7}]},
            headers=auth_headers,
        )
        assert response.status_code == 200

    def test_sale_supply(self, client, db_session, auth_headers):
        """Test supply sale has price = 0"""
        # Create product and production
        create_resp = client.post(
            "/fadel/products",
            json={"name": f"{TEST_PREFIX}Supply Test", "price": 1000.0},
            headers=auth_headers,
        )
        product_id = create_resp.json()["id"]

        client.post(
            "/fadel/production",
            json={"product_id": product_id, "quantity": 20},
            headers=auth_headers,
        )

        # Create supply sale
        response = client.post(
            "/sales",
            json={
                "items": [
                    {"product_id": product_id, "quantity": 5, "sale_type": "supply"}
                ]
            },
            headers=auth_headers,
        )
        assert response.status_code == 200

    def test_sale_insufficient_stock(self, client, db_session, auth_headers):
        """Test sale with insufficient stock returns 400"""
        # Create product with no production (no stock)
        create_resp = client.post(
            "/fadel/products",
            json={"name": f"{TEST_PREFIX}No Stock", "price": 1000.0},
            headers=auth_headers,
        )
        product_id = create_resp.json()["id"]

        # Try to sell more than available (0)
        response = client.post(
            "/sales",
            json={"items": [{"product_id": product_id, "quantity": 5}]},
            headers=auth_headers,
        )
        assert response.status_code == 400
        assert "Insufficient stock" in response.json()["detail"]


class TestInventory:
    """Tests for inventory endpoint"""

    def test_get_inventory(self, client, db_session, auth_headers):
        """Test getting inventory returns correct stock levels"""
        # Create product and production
        create_resp = client.post(
            "/fadel/products",
            json={"name": f"{TEST_PREFIX}Inventory Test", "price": 1000.0},
            headers=auth_headers,
        )
        product_id = create_resp.json()["id"]

        client.post(
            "/fadel/production",
            json={"product_id": product_id, "quantity": 30},
            headers=auth_headers,
        )

        # Get inventory (public endpoint)
        response = client.get(f"/inventory/{product_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["product_name"] == f"{TEST_PREFIX}Inventory Test"
        assert data["production_stock"] == 30
        assert data["current_stock"] == 30

    def test_inventory_nonexistent_product(self, client):
        """Test inventory for non-existent product returns 404"""
        fake_id = str(uuid.uuid4())
        response = client.get(f"/inventory/{fake_id}")
        assert response.status_code == 404


class TestWholesaleClassification:
    """Tests for automatic wholesale classification"""

    def test_auto_classify_wholesale_at_5(self, client, db_session, auth_headers):
        """Test quantity >= 5 auto-classifies as wholesale"""
        # Create product and production
        create_resp = client.post(
            "/fadel/products",
            json={"name": f"{TEST_PREFIX}Auto Wholesale", "price": 1000.0},
            headers=auth_headers,
        )
        product_id = create_resp.json()["id"]

        client.post(
            "/fadel/production",
            json={"product_id": product_id, "quantity": 20},
            headers=auth_headers,
        )

        # Sale with qty = 5 (no explicit sale_type)
        response = client.post(
            "/sales",
            json={"items": [{"product_id": product_id, "quantity": 5}]},
            headers=auth_headers,
        )
        assert response.status_code == 200

    def test_retail_below_5(self, client, db_session, auth_headers):
        """Test quantity < 5 stays as retail"""
        # Create product and production
        create_resp = client.post(
            "/fadel/products",
            json={"name": f"{TEST_PREFIX}Auto Retail", "price": 1000.0},
            headers=auth_headers,
        )
        product_id = create_resp.json()["id"]

        client.post(
            "/fadel/production",
            json={"product_id": product_id, "quantity": 20},
            headers=auth_headers,
        )

        # Sale with qty = 4 (explicit retail)
        response = client.post(
            "/sales",
            json={
                "items": [
                    {"product_id": product_id, "quantity": 4, "sale_type": "retail"}
                ]
            },
            headers=auth_headers,
        )
        assert response.status_code == 200


class TestInputValidation:
    """Tests for input validation"""

    def test_product_name_too_long(self, client, auth_headers):
        """Test product name exceeding max length returns 422"""
        response = client.post(
            "/fadel/products",
            json={"name": "A" * 101, "price": 100.0},
            headers=auth_headers,
        )
        assert response.status_code == 422

    def test_invalid_sale_type(self, client, auth_headers):
        """Test invalid sale_type returns 422"""
        fake_id = str(uuid.uuid4())
        response = client.post(
            "/sales",
            json={
                "items": [
                    {"product_id": fake_id, "quantity": 1, "sale_type": "invalid"}
                ]
            },
            headers=auth_headers,
        )
        assert response.status_code == 422

    def test_quantity_too_large(self, client, auth_headers):
        """Test quantity exceeding max returns 422"""
        fake_id = str(uuid.uuid4())
        response = client.post(
            "/sales",
            json={"items": [{"product_id": fake_id, "quantity": 100001}]},
            headers=auth_headers,
        )
        assert response.status_code == 422
