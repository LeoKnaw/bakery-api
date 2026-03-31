# Bakery API

A FastAPI-based REST API for managing bakery products, production tracking, and inventory.

## Tech Stack

- **Framework:** FastAPI
- **Data Validation:** Pydantic
- **Storage:** In-memory (list-based)
- **Python:** 3.13+

## Data Models

### Product
| Field | Type | Description |
|-------|------|-------------|
| id | UUID | Unique identifier |
| name | string | Product name |
| price | float | Product price (must be > 0) |

### ProductionRecord
| Field | Type | Description |
|-------|------|-------------|
| id | UUID | Unique identifier |
| product_id | UUID | Reference to product |
| quantity | int | Units produced (must be > 0) |
| timestamp | datetime | When production occurred |

### InventoryItem
| Field | Type | Description |
|-------|------|-------------|
| product_id | UUID | Reference to product |
| quantity | int | Current stock (minimum 0) |

## API Endpoints

### Products

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1` | List all products |
| POST | `/fadel/products` | Create a new product |
| PUT | `/fadel/products/{product_id}` | Update a product |
| DELETE | `/fadel/delete/{product_id}` | Delete a product |

### Production

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/fadel/production` | Record production batch |
| GET | `/fadel/production` | List all production records |

### Inventory

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/fadel/inventory` | List all inventory items |
| GET | `/fadel/inventory/{product_id}` | Get inventory for specific product |
| PATCH | `/fadel/inventory/{product_id}` | Manually adjust inventory |

## Business Logic

### Production Flow
1. When production is recorded via `POST /fadel/production`, the system:
   - Validates the product exists
   - Creates a production record with timestamp
   - Automatically increments inventory for that product
   - Creates inventory entry if none exists

### Inventory Rules
- Quantity cannot go below 0
- Manual adjustments via PATCH are validated against negative results
- Inventory automatically reflects production records

## Usage Examples

### Create a Product
```bash
curl -X POST "http://localhost:8000/fadel/products" \
  -H "Content-Type: application/json" \
  -d '{"name": "Croissant", "price": 3.50}'
```

### Record Production
```bash
curl -X POST "http://localhost:8000/fadel/production" \
  -H "Content-Type: application/json" \
  -d '{"product_id": "<uuid>", "quantity": 50}'
```

### Check Inventory
```bash
curl "http://localhost:8000/fadel/inventory"
```

### Adjust Inventory
```bash
curl -X PATCH "http://localhost:8000/fadel/inventory/<product_id>" \
  -H "Content-Type: application/json" \
  -d -5  # Adjust by +5 or -5 (result must be >= 0)
```

## Running the API

```bash
uvicorn bakery:app --reload
```

API docs available at `http://localhost:8000/docs`
