"""Tests for Daily Stock Record endpoints"""

import uuid
from datetime import date, timedelta

TEST_PREFIX = "STOCK_TEST_"

DATE = date.today().isoformat()


class TestDailyStockRecords:
    """Tests for daily stock record endpoints"""

    def test_create_daily_stock_records(self, client, admin_user_headers):
        """Test creating daily stock records for all products"""
        product_response = client.post(
            "/fadel/products",
            json={"name": f"{TEST_PREFIX}Bread", "price": 500.0, "wholesale_price": 450.0},
            headers={"X-API-Key": "test-api-key-2026"},
        )
        assert product_response.status_code == 200

        record_date = date.today().isoformat()
        response = client.post(
            f"/stock/daily?record_date={record_date}",
            headers=admin_user_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["opening_stock"] == 0
        assert data[0]["production_stock"] == 0
        assert data[0]["closing_stock"] == 0

    def test_create_daily_records_duplicate_date(self, client, admin_user_headers):
        """Test that creating records for same date returns error"""
        product_response = client.post(
            "/fadel/products",
            json={"name": f"{TEST_PREFIX}Biscuit", "price": 300.0, "wholesale_price": 270.0},
            headers={"X-API-Key": "test-api-key-2026"},
        )
        assert product_response.status_code == 200

        record_date = date.today().isoformat()
        client.post(
            f"/stock/daily?record_date={record_date}",
            headers=admin_user_headers,
        )

        response = client.post(
            f"/stock/daily?record_date={record_date}",
            headers=admin_user_headers,
        )
        assert response.status_code == 400
        assert "already exist" in response.json()["detail"]

    def test_get_daily_stock_records_by_date(self, client, admin_user_headers):
        """Test filtering records by specific date"""
        product_response = client.post(
            "/fadel/products",
            json={"name": f"{TEST_PREFIX}Cake", "price": 1000.0, "wholesale_price": 900.0},
            headers={"X-API-Key": "test-api-key-2026"},
        )
        assert product_response.status_code == 200

        record_date = date.today().isoformat()
        client.post(
            f"/stock/daily?record_date={record_date}",
            headers=admin_user_headers,
        )

        response = client.get(
            f"/stock/daily?record_date={record_date}",
            headers=admin_user_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1

    def test_get_daily_stock_record_by_id(self, client, admin_user_headers):
        """Test getting a single stock record by ID"""
        product_response = client.post(
            "/fadel/products",
            json={"name": f"{TEST_PREFIX}Donut", "price": 200.0, "wholesale_price": 180.0},
            headers={"X-API-Key": "test-api-key-2026"},
        )
        assert product_response.status_code == 200

        record_date = date.today().isoformat()
        create_response = client.post(
            f"/stock/daily?record_date={record_date}",
            headers=admin_user_headers,
        )
        record_id = create_response.json()[0]["id"]

        response = client.get(
            f"/stock/daily/{record_id}",
            headers=admin_user_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == record_id

    def test_update_daily_stock_record(self, client, admin_user_headers):
        """Test updating a stock record and auto-calculating closing stock"""
        product_response = client.post(
            "/fadel/products",
            json={"name": f"{TEST_PREFIX}Puff", "price": 150.0, "wholesale_price": 135.0},
            headers={"X-API-Key": "test-api-key-2026"},
        )
        assert product_response.status_code == 200

        record_date = date.today().isoformat()
        create_response = client.post(
            f"/stock/daily?record_date={record_date}",
            headers=admin_user_headers,
        )
        record_id = create_response.json()[0]["id"]

        response = client.put(
            f"/stock/daily/{record_id}",
            json={
                "opening_stock": 10,
                "production_stock": 20,
                "wholesale_quantity": 5,
                "retail_quantity": 3,
            },
            headers=admin_user_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["opening_stock"] == 10
        assert data["production_stock"] == 20
        assert data["wholesale_quantity"] == 5
        assert data["retail_quantity"] == 3
        assert data["closing_stock"] == 22  # 10 + 20 - 5 - 3 = 22

    def test_update_daily_stock_record_with_revenue(self, client, admin_user_headers):
        """Test updating stock record with revenue values"""
        product_response = client.post(
            "/fadel/products",
            json={"name": f"{TEST_PREFIX}Roll", "price": 100.0, "wholesale_price": 90.0},
            headers={"X-API-Key": "test-api-key-2026"},
        )
        assert product_response.status_code == 200
        product_id = product_response.json()["id"]

        record_date = date.today().isoformat()
        create_response = client.post(
            f"/stock/daily?record_date={record_date}",
            headers=admin_user_headers,
        )
        record_id = create_response.json()[0]["id"]

        response = client.put(
            f"/stock/daily/{record_id}",
            json={
                "opening_stock": 5,
                "production_stock": 15,
                "wholesale_quantity": 3,
                "retail_quantity": 2,
                "wholesale_revenue": 270.0,
                "retail_revenue": 200.0,
            },
            headers=admin_user_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["wholesale_revenue"] == 270.0
        assert data["retail_revenue"] == 200.0
        assert data["closing_stock"] == 15  # 5 + 15 - 3 - 2 = 15

    def test_get_stock_summary(self, client, admin_user_headers):
        """Test getting stock summary for date range"""
        product_response = client.post(
            "/fadel/products",
            json={"name": f"{TEST_PREFIX}Cookie", "price": 80.0, "wholesale_price": 72.0},
            headers={"X-API-Key": "test-api-key-2026"},
        )
        assert product_response.status_code == 200

        record_date = date.today().isoformat()
        client.post(
            f"/stock/daily?record_date={record_date}",
            headers=admin_user_headers,
        )

        response = client.get(
            f"/stock/summary?start_date={record_date}&end_date={record_date}",
            headers=admin_user_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert "totals" in data
        assert "by_product" in data

    def test_get_daily_stock_records_requires_auth(self, client):
        """Test that getting records requires authentication"""
        response = client.get("/stock/daily")
        assert response.status_code == 401

    def test_update_stock_record_requires_auth(self, client):
        """Test that updating records requires authentication"""
        fake_id = str(uuid.uuid4())
        response = client.put(
            f"/stock/daily/{fake_id}",
            json={"opening_stock": 10},
        )
        assert response.status_code == 401

    def test_closing_stock_calculation(self, client, admin_user_headers):
        """Test various closing stock calculations"""
        product_response = client.post(
            "/fadel/products",
            json={"name": f"{TEST_PREFIX}Pie", "price": 250.0, "wholesale_price": 225.0},
            headers={"X-API-Key": "test-api-key-2026"},
        )
        assert product_response.status_code == 200

        record_date = date.today().isoformat()
        create_response = client.post(
            f"/stock/daily?record_date={record_date}",
            headers=admin_user_headers,
        )
        record_id = create_response.json()[0]["id"]

        response = client.put(
            f"/stock/daily/{record_id}",
            json={
                "opening_stock": 100,
                "production_stock": 50,
                "wholesale_quantity": 30,
                "retail_quantity": 20,
            },
            headers=admin_user_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["closing_stock"] == 100  # 100 + 50 - 30 - 20 = 100


class TestSupplyQuantity:
    """Tests for supply quantity in daily stock records"""

    def test_create_daily_stock_includes_supply_quantity(self, client, admin_user_headers):
        """Test that new daily stock records include supply_quantity field"""
        client.post(
            "/fadel/products",
            json={"name": f"{TEST_PREFIX}Supply1", "price": 500.0, "wholesale_price": 450.0},
            headers={"X-API-Key": "test-api-key-2026"},
        )

        record_date = date.today().isoformat()
        response = client.post(
            f"/stock/daily?record_date={record_date}",
            headers=admin_user_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data) > 0
        assert "supply_quantity" in data[0]
        assert data[0]["supply_quantity"] == 0

    def test_update_stock_record_with_supply(self, client, admin_user_headers):
        """Test updating stock record with supply quantity"""
        client.post(
            "/fadel/products",
            json={"name": f"{TEST_PREFIX}Supply2", "price": 500.0, "wholesale_price": 450.0},
            headers={"X-API-Key": "test-api-key-2026"},
        )

        record_date = date.today().isoformat()
        client.post(
            f"/stock/daily?record_date={record_date}",
            headers=admin_user_headers,
        )

        record_id = client.get(
            f"/stock/daily?record_date={record_date}",
            headers=admin_user_headers,
        ).json()[0]["id"]

        response = client.put(
            f"/stock/daily/{record_id}",
            json={
                "opening_stock": 50,
                "production_stock": 20,
                "wholesale_quantity": 10,
                "retail_quantity": 5,
                "supply_quantity": 3,
            },
            headers=admin_user_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["supply_quantity"] == 3
        assert data["closing_stock"] == 52  # 50 + 20 - 10 - 5 - 3 = 52

    def test_closing_stock_with_supply(self, client, admin_user_headers):
        """Test that closing stock calculation includes supply"""
        client.post(
            "/fadel/products",
            json={"name": f"{TEST_PREFIX}Supply3", "price": 500.0, "wholesale_price": 450.0},
            headers={"X-API-Key": "test-api-key-2026"},
        )

        record_date = date.today().isoformat()
        client.post(
            f"/stock/daily?record_date={record_date}",
            headers=admin_user_headers,
        )

        record_id = client.get(
            f"/stock/daily?record_date={record_date}",
            headers=admin_user_headers,
        ).json()[0]["id"]

        response = client.put(
            f"/stock/daily/{record_id}",
            json={
                "opening_stock": 100,
                "production_stock": 50,
                "wholesale_quantity": 30,
                "retail_quantity": 20,
                "supply_quantity": 10,
            },
            headers=admin_user_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["closing_stock"] == 90  # 100 + 50 - 30 - 20 - 10 = 90

    def test_supply_does_not_affect_revenue(self, client, admin_user_headers):
        """Test that supply quantity does not affect revenue"""
        client.post(
            "/fadel/products",
            json={"name": f"{TEST_PREFIX}Supply4", "price": 500.0, "wholesale_price": 450.0},
            headers={"X-API-Key": "test-api-key-2026"},
        )

        record_date = date.today().isoformat()
        client.post(
            f"/stock/daily?record_date={record_date}",
            headers=admin_user_headers,
        )

        record_id = client.get(
            f"/stock/daily?record_date={record_date}",
            headers=admin_user_headers,
        ).json()[0]["id"]

        response = client.put(
            f"/stock/daily/{record_id}",
            json={
                "opening_stock": 50,
                "production_stock": 20,
                "wholesale_quantity": 10,
                "retail_quantity": 5,
                "wholesale_revenue": 1000.0,
                "retail_revenue": 500.0,
                "supply_quantity": 15,
            },
            headers=admin_user_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["wholesale_revenue"] == 1000.0
        assert data["retail_revenue"] == 500.0
        assert data["supply_quantity"] == 15

    def test_supply_in_summary(self, client, admin_user_headers):
        """Test that supply quantity appears in summary"""
        client.post(
            "/fadel/products",
            json={"name": f"{TEST_PREFIX}Supply5", "price": 500.0, "wholesale_price": 450.0},
            headers={"X-API-Key": "test-api-key-2026"},
        )

        record_date = date.today().isoformat()
        client.post(
            f"/stock/daily?record_date={record_date}",
            headers=admin_user_headers,
        )

        response = client.get(
            f"/stock/summary?start_date={record_date}&end_date={record_date}",
            headers=admin_user_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert "supply_quantity" in data["totals"]
        assert data["totals"]["supply_quantity"] == 0
