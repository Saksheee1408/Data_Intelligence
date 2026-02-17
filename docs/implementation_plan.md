# Weak Signal Intelligence -- Simple MVP Plan

## Executive Summary
This is a lightweight Minimum Viable Product (MVP) designed to demonstrate the core value of "Weak Signal Intelligence" without any infrastructure bloat. It runs as a simple web application using standard, easy-to-deploy technologies.

## 1. Simple Tech Stack (The "MVP" Approach)
We are avoiding all complex orchestration and distributed systems.

*   **Frontend**:
    *   **Angular** (Latest version): Standard structure for the web interface.
    *   **Tailwind CSS**: For clean, modern styling.
    *   **Charts**: ECharts or Ngx-Charts for visualizing trends.
*   **Backend**:
    *   **FastAPI** (Python): A fast, modern web framework.
    *   **SQLite**: A single-file database. No installation or server management required.
*   **Intelligence**:
    *   **Pandas**: Analysis library to detect signals in-memory.
    *   **Simple Background Tasks**: Using standard Python `asyncio` for fetching data (no Redis/Celery required).

---

## 2. Simplified Architecture

1.  **User Interface (Angular)**
    *   A Dashboard to upload files and view alerts.
    *   A "Signal Feed" to see detected risks.

2.  **API Server (FastAPI)**
    *   Receives CSV uploads (Sales, Inventory) and stores them in SQLite.
    *   Runs python functions to detect anomalies.
    *   Serves the detected signals to the frontend.

3.  **Data Storage (SQLite)**
    *   `products`: List of items.
    *   `transactions`: Historical sales data.
    *   `signals`: The detected weak signals (e.g., "Stock Dropping").

---

## 3. Implementation Roadmap

### Phase 1: Core Setup & Data Entry (Days 1-2)
*   **Project Init**: Create a folder with `frontend/` (Angular) and `backend/` (FastAPI).
*   **Database**: Set up `database.db` (SQLite) with simple tables using SQLAlchemy.
*   **Upload Feature**:
    *   Backend: Endpoint to accept CSV files and save to DB.
    *   Frontend: Simple page to drag & drop "Sales.csv" and "Stock.csv".

### Phase 2: The Logic Engine (Days 3-4)
*   **Signal Detection Algorithm**:
    *   Write a Python function `detect_stock_drops()` that queries SQLite into a Pandas DataFrame.
    *   Identify items where stock is falling but no sales are recorded.
*   **Alert Generation**: Save these findings into the `signals` table.
*   **Dashboard Feed**: Create a list view in Angular to show these alerts.

### Phase 3: External Context & Polish (Day 5)
*   **Context Fetcher**: When a signal is found, call a lightweight news API (e.g., Google News RSS) for keywords related to that product.
*   **Visualization**: Add a simple line chart showing the stock drop trend for the selected signal.

---

## 4. Why This is "MVP"
*   **Zero Infrastructure**: Runs on a single laptop or cheap VPS.
*   **No "Big Data"**: No Spark, No Kubernetes, No Data Lake.
*   **Instant Setup**: Just `npm start` and `python main.py`.
