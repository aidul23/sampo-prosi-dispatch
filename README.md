# Sampo Dispatch Planning Demo

A small web-based dispatch planning demo for a transport company that currently
plans its daily deliveries in Excel. The demo mirrors the existing spreadsheet
workflow: import the daily Excel order sheet, edit orders in a table, assign
delivery drivers, check truck capacity, and export driver-specific delivery
lists back to Excel.

**This is a rule-based operational demo — not an AI solution.** The structure
is intentionally simple and clean so it can be extended with AI features later.

## Tech stack

- **Frontend:** React + Vite + TypeScript (plain CSS, `useState` only)
- **Backend:** Python FastAPI
- **Excel processing:** pandas + openpyxl
- **Storage:** in-memory only (no database, no authentication)

## Project structure

```
sampo-dispatch-demo/
  README.md
  backend/
    app/
      main.py              # FastAPI endpoints
      models.py            # Pydantic data models
      excel_service.py     # Excel import/export
      planning_service.py  # Pallet conversion & capacity logic
      sample_data.py       # Demo orders
    requirements.txt
  frontend/
    src/
      App.tsx
      api/client.ts        # All API calls
      types/dispatch.ts    # Shared TypeScript interfaces
      components/          # FileUpload, OrderTable, RouteSummary, DriverPlan, Toolbar
      utils/pallet.ts      # FIN-equivalent conversion (mirrors backend)
      styles.css
```

## How to run

### Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:5173. The Vite dev server proxies `/api/*` requests to
the backend on port 8000.

## Deploy for client demo

The app has two parts: a static React frontend (GitHub Pages) and a Python API
backend (Render free tier). GitHub Pages cannot run the backend, so both are
needed for the full demo (Excel upload, planning, export).

### 1. Deploy the backend on Render

1. Sign in at [render.com](https://render.com) and connect the GitHub repo
   `aidul23/sampo-prosi-dispatch`.
2. Create a **Blueprint** from the repo (it picks up `render.yaml` at the root),
   or create a **Web Service** manually:
   - Root directory: `backend`
   - Build: `pip install -r requirements.txt`
   - Start: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
3. After deploy, note the service URL, e.g.
   `https://sampo-dispatch-api.onrender.com`.

The free tier sleeps after inactivity; the first request may take ~30 seconds.

### 2. Configure GitHub Pages

1. In the repo on GitHub: **Settings → Secrets and variables → Actions**.
2. Add a repository secret:
   - Name: `VITE_API_URL`
   - Value: your Render API URL + `/api`, e.g.
     `https://sampo-dispatch-api.onrender.com/api`
3. **Settings → Pages → Build and deployment → Source:** choose **GitHub Actions**.

### 3. Publish the frontend

Push to `main` (or run the **Deploy to GitHub Pages** workflow manually). The
site will be available at:

**https://aidul23.github.io/sampo-prosi-dispatch/**

Share that link with the client for feedback. Data is session-only in the browser;
refresh clears it.

## API endpoints

| Method | Endpoint                    | Description                                                        |
| ------ | --------------------------- | ------------------------------------------------------------------ |
| POST   | `/api/upload-excel`         | Upload an Excel order sheet, returns parsed orders as JSON          |
| GET    | `/api/sample-orders`        | Returns built-in sample demo orders                                 |
| POST   | `/api/calculate-plan`       | Calculates FIN-equivalent loads, per-driver usage, overload warnings |
| POST   | `/api/export-driver-sheets` | Generates a downloadable Excel workbook with driver sheets          |
| GET    | `/api/health`               | Health check                                                        |

## Demo workflow

1. **Load orders** — upload the daily Excel sheet, or click *Load sample data*.
2. **Edit orders** — change pallets, pallet type, stackable, delivery driver,
   route area, status, and extra info directly in the table. Add or delete rows.
3. **Set drivers** — define drivers and truck capacities (defaults:
   Driver A = 48, Driver B = 44, Driver C = 40 FIN units).
4. **Calculate plan** — see per-driver capacity usage and clear overload
   warnings on routes that exceed truck capacity.
5. **Create next day plan** — removes DELIVERED orders, keeps CARRY_OVER and
   remaining orders for the next day.
6. **Export driver sheets** — downloads one Excel workbook containing a
   *Full Plan* sheet, one sheet per delivery driver, and a *Route Summary* sheet.

## Pallet conversion rules

FIN pallet (1200 × 1000 mm) is the base unit:

| Pallet type | FIN equivalent |
| ----------- | -------------- |
| FIN         | 1.0            |
| EUR (1200 × 800) | 0.8       |
| OTHER       | 1.0            |

If an order is **stackable**, its effective load is divided by 2.
Examples: 10 FIN not stackable = 10.0 · 10 EUR not stackable = 8.0 ·
10 FIN stackable = 5.0 · 10 EUR stackable = 4.0.

## Excel import assumptions

Customer Excel sheets may not have perfect headers, so parsing is flexible and
modelled on the customer's real daily sheet:

- The header row is auto-detected anywhere in the first 15 rows (real sheets
  have date/title rows above the headers).
- Headers are matched by name in English or Finnish:
  `customer/asiakas/lähettäjä`, `pickup driver/noutokuljettaja`,
  `consignee/vastaanottaja`, `pallets/lavat`, `extra info/lisätieto`,
  `delivery driver/jakokuljettaja/kuski` (plus optional `pallet type`,
  `stackable`, `route area`, `status`).
- Columns the header row leaves unnamed (e.g. pickup driver and extra info in
  the customer's sheet) are filled in by position:
  A = customer, B = pickup driver, C = consignee, D = pallets, E = extra info,
  F = delivery driver.
- Grouped customers are supported: if the customer cell is empty but the row
  has a consignee, the customer is inherited from the row above (matches how
  the sheet lists one customer with many consignee rows).
- Imported `lavat` values are treated as FIN units (pallet type FIN), since
  the customer already converts pallet counts to FIN equivalents by hand.
- Fully empty rows are skipped, unparseable pallet counts become 0, and IDs
  are generated automatically.

## Other assumptions

- Truck capacity is expressed in FIN pallet units.
- An order assigned to a driver without a defined capacity gets a warning.
- Data lives only in browser memory during the session — refresh clears it.
- This is a customer demo, not production software.

## Future AI extension ideas

- **Automatic route assignment:** suggest the optimal driver per order based on
  route area, capacity, and historical patterns.
- **Load optimisation:** pack trucks optimally considering stackability,
  weight, and delivery sequence.
- **Excel intelligence:** ML-assisted column mapping and data cleaning for any
  customer spreadsheet format.
- **Demand forecasting:** predict daily volumes per route from history.
- **Delivery time windows:** ETA prediction and time-window aware planning.
- **Natural language interface:** "Move all Nokia orders to Driver B" style
  commands on top of the structured plan.
