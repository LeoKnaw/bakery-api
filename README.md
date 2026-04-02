# Fadel Bakery API

A full-stack bakery management system for tracking products, production, sales, and inventory. Includes automatic daily email reports.

## Live URLs

| Service | URL |
|---------|-----|
| **API** | https://fadel-api.onrender.com |
| **Frontend** | https://fadel-bakery.onrender.com |
| **API Docs** | https://fadel-api.onrender.com/docs |

## Tech Stack

| Component | Technology |
|-----------|------------|
| **Backend** | FastAPI, SQLAlchemy, Pydantic |
| **Database** | PostgreSQL (Supabase) |
| **Frontend** | Streamlit |
| **Deployment** | Render |
| **Email** | Gmail SMTP |
| **Auth** | API Key + JWT tokens |

## Features

### Authentication
- User registration with admin approval
- First user auto-approved as admin
- API key authentication for operations
- User token authentication for admin panel

### Products (Admin Only)
- Create, update, deactivate products
- Soft delete (deactivation) preserves history
- Auto-calculated wholesale price (10% discount)

### Production
- Record baking/production batches
- Automatic inventory updates
- Production history tracking

### Sales
- **Retail:** Qty < 5, full price
- **Wholesale:** Qty ≥ 5, 10% discount
- **Supply:** Inventory tracking only, no revenue
- Automatic sale type classification
- Stock validation with detailed error messages

### Inventory
- Real-time stock tracking
- Opening stock, production, sales, closing stock
- Date-based inventory reports

### Daily Email Reports
- Automatic reports sent at 9pm Nigerian time (WAT)
- Wholesale/retail/supply breakdown
- Revenue calculations
- Stock levels per product

### Timezone
- All timestamps in Nigerian time (WAT, UTC+1)
- Database and frontend show same local time

## API Endpoints

### Authentication
| Method | Endpoint | Description | Auth |
|--------|----------|-------------|------|
| POST | `/auth/register` | Register new user | Public |
| POST | `/auth/login` | Login, get token | Public |
| GET | `/auth/pending` | List pending users | Admin |
| POST | `/auth/approve/{user_id}` | Approve user | Admin |
| GET | `/auth/users` | List all users | Admin |

### Products
| Method | Endpoint | Description | Auth |
|--------|----------|-------------|------|
| GET | `/fadel/products` | List active products | Public |
| POST | `/fadel/products` | Create product | API Key |
| PUT | `/fadel/products/{id}` | Update product | API Key |
| PATCH | `/fadel/products/{id}/deactivate` | Deactivate product | API Key |

### Production
| Method | Endpoint | Description | Auth |
|--------|----------|-------------|------|
| GET | `/fadel/production` | List production records | Public |
| POST | `/fadel/production` | Record production | API Key |

### Sales
| Method | Endpoint | Description | Auth |
|--------|----------|-------------|------|
| POST | `/sales` | Create sale | API Key |

### Inventory
| Method | Endpoint | Description | Auth |
|--------|----------|-------------|------|
| GET | `/inventory/{product_id}` | Get inventory for product | Public |

## Running Locally

### Prerequisites
- Python 3.13+
- Supabase database

### Setup

1. Clone the repository:
```bash
git clone https://github.com/LeoKnaw/bakery-api.git
cd bakery-api
```

2. Install dependencies:
```bash
pip install -r .venv/requirements.txt
```

3. Create `.venv/.env` file:
```env
DATABASE_URL=postgresql://postgres:YOUR_PASSWORD@YOUR_HOST:5432/postgres?sslmode=require
API_KEY=your-secret-api-key
EMAIL_ADDRESS=your@gmail.com
EMAIL_PASSWORD=your-app-password
REPORT_RECIPIENT=recipient@email.com
```

4. Start the API:
```bash
cd .venv
uvicorn bakery:app --reload
```

5. Start the frontend (separate terminal):
```bash
cd .venv
streamlit run streamlit_app.py
```

## Deployment

Deployed on Render using Docker. See `render.yaml` for service configuration.

### Services
- `fadel-api` - FastAPI backend
- `fadel-bakery` - Streamlit frontend
- `fadel-daily-report` - Cron job (runs daily at 9pm WAT)

### Required Environment Variables

| Variable | Description |
|----------|-------------|
| `DATABASE_URL` | Supabase connection string |
| `API_KEY` | API authentication key |
| `EMAIL_ADDRESS` | Gmail address for reports |
| `EMAIL_PASSWORD` | Gmail app password |
| `REPORT_RECIPIENT` | Email to receive reports |
| `BASE_URL` | API URL (for Streamlit) |

## Project Structure

```
.venv/
├── bakery.py          # FastAPI application
├── models.py          # SQLAlchemy models
├── schema.py          # Pydantic schemas
├── database.py        # Database connection
├── mailing.py         # Email report logic
├── api_client.py      # API client for Streamlit
├── streamlit_app.py   # Streamlit frontend
├── requirements.txt   # Python dependencies
├── Dockerfile.api     # API Docker config
├── Dockerfile.streamlit # Frontend Docker config
├── Dockerfile.cron    # Cron job Docker config
└── tests/
    ├── conftest.py    # Test fixtures
    └── test_bakery.py # API tests (29 tests)
```

## License

MIT
