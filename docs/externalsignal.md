# Weak Signal Intelligence -- External Signals Strategy & Implementation

## 1. Real-Time Signal Architecture

To move beyond static hardcoding, we will implement a real-time fetching engine that continuously senses the external environment.

### Data Sources (MVP Phase)
*   **Google News RSS**: `https://news.google.com/rss/search?q={TOPIC}`
    *   Topics: "Gold Price", "Jewellery Market", "Diamond Supply Chain", "Luxury Retail Trends", "Global Inflation".
*   **Financial Indicators**:
    *   (Future) Yahoo Finance API / Alpha Vantage for raw numbers (Gold Spot Price, USD/INR).

### Processing Pipeline
1.  **Fetch**: Periodically (e.g., every 15-60 mins) poll the RSS feeds for the target industry.
2.  **Deduplicate**: Check against the database to ensure we don't re-ingest the same headline.
3.  **Sentiment Analysis**: 
    *   Use NLP (e.g., `TextBlob` or `VADER`) to score headlines.
    *   Negative Sentiment -> Potential Risk/High Severity.
    *   Positive Sentiment -> Potential Opportunity.
4.  **Classification**: Tag signals as "Economic", "Supply Chain", "Regulatory", etc. based on keywords.

## 2. Universal External Signal Dimensions

### Economic
*   Inflation, commodity price, currency, interest rate.
*   *Keywords*: "Inflation", "Rates", "Price", "Recession".

### Policy & Regulation
*   Tax discussions, bans, approvals, compliance rules.
*   *Keywords*: "Regulation", "Tax", "Ban", "Compliance", "Law".

### Consumer Behavior
*   Search trends, sentiment shifts, enquiry rise.
*   *Keywords*: "Consumer", "Spending", "Trend", "Demand".

### Supply Chain
*   Raw material shortage, logistics delay, vendor instability.
*   *Keywords*: "Supply", "Shortage", "Logistics", "Shipping".

### Technology Disruption
*   Automation adoption, AI innovation, competitor tech shift.
*   *Keywords*: "AI", "Technology", "Innovation", "Digital".

------------------------------------------------------------------------

## 3. Context‑Driven External Activation

*   External sensing depends on internal business condition.
*   Rising demand → watch price, supply, logistics.
*   Falling sales → watch sentiment, economy, competitors.

------------------------------------------------------------------------

## 4. Nature of True Weak Signals

*   Slow repetition instead of sudden spikes.
*   Subtle discussions before official news.
*   Behavioral shifts before measurable demand.

------------------------------------------------------------------------

## 5. Implementation Roadmap

1.  **Integrate `feedparser`**: Robust parsing of RSS feeds.
2.  **Integrate `TextBlob`**: Local, privacy-friendly sentiment analysis.
3.  **Background Scheduler**: Automate fetching without blocking the main API.
4.  **Dashboard Integration**: Show these live signals on the main dashboard.

**Goal:** Sense tiny future disturbances before real‑world change occurs.



**New prompts:**
Update the existing prototype logic WITHOUT changing any UI.

Goal:
When the user uploads the CSV, the backend must extract BOTH:
1) Internal signals from numeric patterns in the CSV
2) External signals from “external-like” information present in the SAME CSV (i.e., derive external signals by interpreting CSV columns such as cost/lead-time/stock trends as external pressure indicators). Do NOT use any hardcoded external signals and do NOT call any external API for this version.

Scope:
Keep the current Angular UI exactly the same. Only change backend processing + response mapping so the UI shows internal_signals and external_signals based on the uploaded CSV.

Input CSVs supported:
A) Jewellery CSV schema:
date,sales_inr,gold_stock_gm,supplier_delay_days,advance_bookings
B) EV CSV schema:
date,production_units,battery_stock_units,supplier_lead_time_days,battery_cost_per_unit

Backend changes (FastAPI):
1) Keep endpoint:
POST /demo/upload (or your existing upload endpoint) accepting multipart/form-data field "file"
2) Detect which dataset type it is (Jewellery vs EV) by checking columns.
3) Parse CSV using pandas, validate required columns, parse date, sort by date.

Internal Signal Extraction (from CSV only):
- Jewellery internal rules:
  a) Stock decreasing in last 3 rows: gold_stock_gm day3 < day2 < day1
     signal="Gold stock is continuously decreasing", metric="gold_stock_gm", severity=0.70
  b) Supplier delay increasing: supplier_delay_days(last) - supplier_delay_days(first of last3) >= 1
     signal="Supplier delivery delay is increasing", metric="supplier_delay_days", severity=0.65
  c) Advance bookings rising in last 3 rows: advance_bookings day3 > day2 > day1
     signal="Advance bookings are rising", metric="advance_bookings", severity=0.60

- EV internal rules:
  a) Battery stock decreasing in last 3 rows: battery_stock_units day3 < day2 < day1
     signal="Battery stock is continuously decreasing", metric="battery_stock_units", severity=0.70
  b) Supplier lead time increasing: supplier_lead_time_days(last) - supplier_lead_time_days(first of last3) >= 1
     signal="Supplier lead time is increasing", metric="supplier_lead_time_days", severity=0.65
  c) Production rising but stock falling (last 3 rows): production_units increasing AND battery_stock_units decreasing
     signal="Production pressure rising while stock is falling", metric="production_units+battery_stock_units", severity=0.75

External Signal Extraction (from SAME CSV only; derived indicators, not hardcoded):
- Jewellery external-like derived signals:
  a) If supplier_delay_days trend is increasing over last 5 rows -> external_signal:
     "Supply chain pressure increasing (delivery delays rising)"
     confidence=0.65
  b) If sales_inr 5-day moving average drops > 8% vs previous 5-day avg -> external_signal:
     "Demand-side weakness forming (sales momentum declining)"
     confidence=0.60
  c) If advance_bookings rising while stock falling -> external_signal:
     "Upcoming demand spike risk with limited supply"
     confidence=0.70

- EV external-like derived signals:
  a) If battery_cost_per_unit increases over last 5 rows by >= 5% -> external_signal:
     "Input cost pressure rising (battery cost increasing)"
     confidence=0.70
  b) If supplier_lead_time_days increases over last 5 rows -> external_signal:
     "Logistics / supplier disruption risk increasing"
     confidence=0.65
  c) If production_units increasing and battery_cost_per_unit increasing -> external_signal:
     "Margin risk forming (higher input cost during scaling)"
     confidence=0.60

Output JSON (must match existing UI bindings; do not change UI):
Return:
{
  "dataset_type": "jewellery" or "ev",
  "internal_signals": [
    {"signal","metric","strength":"weak","severity","timestamp"}
  ],
  "external_signals": [
    {"signal","dimension":"supply_chain|economic|consumer_behavior","confidence","timestamp"}
  ]
}
- timestamp must be the latest CSV date.
- If no signals found, return empty arrays (UI should show “No signals detected”).

Important constraints:
- Do not change any UI components, labels, or layout.
- Do not hardcode external signals; they must be computed from the uploaded CSV only.
- No external API calls in this version.
