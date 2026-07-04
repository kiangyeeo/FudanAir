<p align="center">
  <img src="docs/logo/logo.png" alt="FudanAir logo" width="96" />
</p>

<h1 align="center">FudanAir Airline Ticketing System</h1>

<p align="center">
  A full-stack airline ticketing and database management system.
</p>



## Overview

FudanAir is a local development project for an airline ticketing management system. It models a realistic booking workflow around flight search, seat inventory, order payment, ticket refund/change operations, and an admin console for operational data management.

The system keeps the database model explicit and course-friendly: simple CRUD is implemented with SQLAlchemy ORM, while complex search, reporting, transit planning, and aggregation logic use hand-written SQL.

## Features

- Passenger flight search with direct flights, nearby-airport alternatives, and transit options.
- Order creation, 15-minute payment window, simulated payment, cancellation, and automatic inventory restoration.
- Ticket refund and flight-change workflows with fee tiers and price-difference calculation.
- User center for profile, password, and saved passenger management.
- Admin console for cities, airports, airlines, aircraft types, flights, flight instances, pricing, orders, and dashboard metrics.
- Scheduled jobs for order expiration, flight-instance generation, and flight-status synchronization.
- Inventory consistency between `cabin_price.available_seats` and `flight_instance.economy_left` / `first_left`.
- English UI and API-facing messages while preserving the original database enum values and seed data.

## Quick Start

### 1. Clone the repository

```bash
git clone https://github.com/kiangyeeo/FudanAir.git
cd FudanAir
```

### 2. Configure the backend environment

Windows PowerShell:

```powershell
cd backend
Copy-Item .env.example .env
```

macOS or Linux:

```bash
cd backend
cp .env.example .env
```

Edit `backend/.env` and replace `YOUR_PASSWORD` in `DB_URL` with your local MySQL password.

### 3. Install backend dependencies

Windows PowerShell:

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

macOS or Linux:

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 4. Initialize the database

```bash
cd backend
python scripts/init_db.py
```

This command recreates the configured database, executes `scripts/schema.sql`, loads CSV seed data, generates flight instances and cabin prices, and creates the default admin account.

Default admin account:

```text
Admin ID: A001
Password: admin123
```

### 5. Start the backend

```bash
cd backend
python start.py
```

The API runs at:

```text
http://127.0.0.1:8000
```

### 6. Start the frontend

Open a second terminal from the repository root:

```bash
cd frontend
npm install
npm run dev
```

The web app runs at:

```text
http://localhost:5173
```

The Vite dev server proxies `/api` requests to `http://127.0.0.1:8000`.

## Test and Verification

Run backend tests:

```bash
cd backend
python -m pytest
```

Run frontend type checks:

```bash
cd frontend
npm run type-check
```

Build the frontend:

```bash
cd frontend
npm run build
```

Run the concurrent booking demo:

```bash
cd backend
python scripts/demo_concurrent_booking.py
```

The concurrency demo sends multiple booking requests for limited stock and verifies that the system prevents overselling.

## Main Workflows

### Passenger Workflow

1. Register or sign in as a passenger.
2. Search flights by departure city, arrival city, date, and filters.
3. Select a direct, nearby-airport, or transit itinerary.
4. Add passengers and create an order.
5. Complete simulated payment before the order expires.
6. View orders, upcoming trips, refund quotes, and change-flight options.

### Admin Workflow

1. Sign in at `/admin/login` with the default admin credentials or a configured admin account.
2. Review dashboard metrics.
3. Manage cities, airports, airlines, aircraft types, flights, generated flight instances, fare tiers, and orders.
4. Adjust flight-instance times or route data and let passenger-facing order details surface adjustment labels.

## Design Notes

- Transaction boundaries are owned by service/workflow code, not repository code.
- Domain modules do not import one another directly; cross-domain orchestration belongs in `workflows/`.
- Seat inventory changes must go through `FlightService.deduct_seat` and `FlightService.restore_seat`.
- Airport-city consistency is maintained by the airport service when city or airport records change.
- Complex SQL is intentionally visible for search, aggregation, dashboard, and transit logic.

## Development Tips

- Re-run `python scripts/init_db.py` after changing schema or seed data. This resets the local database.
- Keep backend and frontend terminals open during manual testing.
- Use the FastAPI `/docs` page to inspect request and response contracts.
- Do not edit seed data or database schema unless the related business requirement is confirmed.
