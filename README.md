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
      route_optimizer_service.py  # Route area assignment optimization
      stop_optimizer_service.py   # Stop sequence (nearest-neighbor)
      address_parser.py           # Find street/postal code in free text
      address_book.py             # Consignee address register (SQLite)
      geocoding_service.py        # Address -> coordinates (Nominatim, cached)
      routing_service.py          # Road distance matrix (OSRM)
      area_distances.py           # Tampere-region area distance matrix
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
   - **Python version: 3.12** (required — 3.14 has no pre-built wheels for pydantic/pandas)
   - Build: `pip install --upgrade pip && pip install -r requirements.txt`
   - Start: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
3. After deploy, note the service URL, e.g.
   `https://sampo-dispatch-api.onrender.com`.

The free tier sleeps after inactivity; the first request may take ~30 seconds.

### 2. Configure GitHub Pages

1. In the repo on GitHub: **Settings → Secrets and variables → Actions**.
2. Add a repository secret:
   - Name: `VITE_API_URL`
   - Value: your Render service URL **with** `/api` at the end, e.g.
     `https://sampo-prosi-dispatch.onrender.com/api`
     (Using only the host, without `/api`, breaks load/calculate/export until you redeploy.)
3. **Settings → Pages → Build and deployment → Source:** choose **GitHub Actions**
   (not “Deploy from a branch”). If this is not set, the deploy job fails with a 404.

### 3. Publish the frontend

Push to `main` (or run the **Deploy to GitHub Pages** workflow manually). The
site will be available at:

**https://aidul23.github.io/sampo-prosi-dispatch/**

Share that link with the client for feedback. Plans can be **saved on the server**
(SQLite on Render); a **local browser draft** is also kept automatically.

## API endpoints

| Method | Endpoint                    | Description                                                        |
| ------ | --------------------------- | ------------------------------------------------------------------ |
| GET    | `/api/plans`                | List saved plans (summary)                                         |
| GET    | `/api/plans/{id}`           | Load a saved plan                                                  |
| POST   | `/api/plans`                | Save a new plan                                                    |
| PUT    | `/api/plans/{id}`           | Update an existing saved plan                                      |
| DELETE | `/api/plans/{id}`           | Delete a saved plan                                                |
| POST   | `/api/geocode-orders`       | Locate order addresses (batched; call again while `pending` > 0)    |
| GET    | `/api/address-book`         | List the consignee address register                                 |
| POST   | `/api/address-book`         | Add / replace a consignee address                                   |
| POST   | `/api/address-book/bulk`    | Save many consignee addresses at once                               |
| PUT    | `/api/address-book/{id}`    | Edit a register entry                                               |
| DELETE | `/api/address-book/{id}`    | Delete a register entry                                             |
| POST   | `/api/address-book/apply`   | Fill empty order addresses from the register                        |
| GET    | `/api/area-centroids`       | Area lat/lng centroids for map display                               |
| POST   | `/api/upload-excel`         | Upload an Excel order sheet, returns parsed orders as JSON          |
| GET    | `/api/sample-orders`        | Returns built-in sample demo orders                                 |
| POST   | `/api/calculate-plan`       | Calculates FIN-equivalent loads, per-driver usage, overload warnings |
| POST   | `/api/optimize-routes`      | Suggests driver assignments by route area and capacity (preview)      |
| POST   | `/api/optimize-stop-order`    | Suggests delivery stop sequence per driver (nearest-neighbor)       |
| POST   | `/api/export-driver-sheets` | Generates a downloadable Excel workbook with driver sheets          |
| GET    | `/api/health`               | Health check                                                        |

## Demo workflow

1. **Load orders** — upload the daily Excel sheet, or click *Load sample data*.
2. **Save / load plans** — use *Saved plans* to **Save as new**, **Update saved plan**,
   **Load**, or **Delete**. Work is also auto-saved as a local browser draft.
3. **Edit orders** — change fields in the table, **+ Add order**, remove a row (×),
   or **Clear all**.
4. **Set drivers** — define drivers and truck capacities (defaults:
   Driver A = 48, Driver B = 44, Driver C = 40 FIN units).
5. **Optimize routes** (optional) — auto-assign unassigned orders to drivers
   by route area and truck capacity. Review the preview, then **Apply** or
   **Apply & calculate**. Check *Include already assigned orders* to re-optimize
   the full plan.
6. **Optimize stop order** (optional) — after drivers are assigned, sequence
   stops within each route from the Lapväärtti terminal (Porintie 382) using
   approximate area distances. Review and **Apply stop order**.
7. **Calculate plan** — see per-driver capacity usage and clear overload
   warnings on routes that exceed truck capacity.
8. **Create next day plan** — removes DELIVERED orders, keeps CARRY_OVER and
   remaining orders for the next day.
9. **Export driver sheets** — downloads one Excel workbook containing a
   *Full Plan* sheet, one sheet per delivery driver (with **Stop #** when
   sequenced), and a *Route Summary* sheet.
10. **Route map** — read-only OpenStreetMap view with pins colored by driver
   and dashed route lines from the Lapväärtti depot (Porintie 382).

## Delivery addresses (accurate map & routes)

Addresses are optional — without one, an order is placed at its route area
centre exactly as before. With one, the order is placed at its real location
and stop order uses real road distances.

**Where an address can come from** (first match wins):

1. An **address column** in the Excel (`Osoite`, `Toimitusosoite`,
   `Katuosoite`, `Address`, `Delivery address`), e.g. column G.
2. **Inside the consignee cell**, e.g. `Valio, Tuupakantie 10, 01740 Vantaa`.
   Street + number and/or postal code + city are extracted; names, phone
   numbers and door codes are ignored. A postal code alone already helps.
3. The **address register** — each recurring consignee's address is stored
   once and filled into orders that have none (matching ignores case,
   accents, phone numbers and door codes).

Addresses can also be typed or edited in the order table.

**Locate addresses** turns addresses into coordinates using OpenStreetMap
Nominatim (free; max 1 request/second). Results — including "not found" —
are cached in SQLite, so each address is looked up only once. Lookup order:
full address → postal code + city → route area centre. The dot next to each
address shows the result: green = exact address, yellow = postal code area,
grey = route area centre.

**Optimize stop order** requests a road distance matrix from OSRM for each
driver's stops (located ones at their coordinates, others at their area
centre). If the routing service is unavailable it falls back to approximate
distances, and the preview notes say which was used.

Configuration (environment variables on the backend):

| Variable | Default | Purpose |
| -------- | ------- | ------- |
| `GEOCODING_ENABLED` | `1` | `0` disables geocoder requests (cache still used) |
| `GEOCODER_URL` | `https://nominatim.openstreetmap.org/search` | Nominatim-compatible endpoint |
| `ROUTING_ENABLED` | `1` | `0` disables road distances |
| `OSRM_URL` | `https://router.project-osrm.org` | OSRM server for road distances |
| `LONG_ROUTE_KM` | `900` | Round-trip km above which routes are penalised in driver assignment |

Note: addresses are sent to these external services. The public Nominatim
and OSRM demo servers are fine for a demo; for daily production use, switch
to a self-hosted or commercial service (e.g. Digitransit, Google, HERE).

## Route optimization rules

**Driver assignment** (capacitated vehicle routing, explainable):

- Every order is placed at its geocoded address, or its route area centre.
  Orders with no known location (no address, unknown area) are left for the
  planner; DELIVERED orders are never moved.
- Trucks without orders get a starting stop in a distinct region
  (farthest-first), so trucks cover different directions.
- Remaining orders are inserted where they add the fewest kilometres
  (regret insertion — orders with only one good option are placed first),
  never exceeding a truck's FIN capacity.
- Local search then moves and swaps orders between trucks (and re-orders
  stops with 2-opt / or-opt) while that shortens total driving distance.
- Routes longer than `LONG_ROUTE_KM` (default 900 km round trip) are
  penalised, so far-apart regions (e.g. Helsinki + Oulu) are not merged into
  one very long route. A truck may stay unused if it is not needed.
- Each suggested change explains the trade-off, e.g. "Adds ~35 km to
  Driver B's route (Driver A would add ~210 km)"; notes show each truck's
  load, round-trip km and main areas.
- `unassigned_only` mode (default) keeps existing driver assignments.

**Stop sequencing**:

- Uses road distances (OSRM) between geocoded addresses when available;
  otherwise approximate distances (local area matrix, or straight line × 1.25).
- Round trip from the depot (**Lapväärtti / Porintie 382**) and back:
  nearest-neighbour tour improved with 2-opt and or-opt.
- Driver sheets and the delivery list UI show **Stop #** after applying.

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
- If the sheet has no **route area** column, it is **auto-parsed from
  Vastaanottaja (consignee)** — e.g. `Valio Espoo` → Espoo, `Lidl Laukaa` →
  Laukaa. Unrecognized names become `Unspecified` with a warning.
- Fully empty rows are skipped, unparseable pallet counts become 0, and IDs
  are generated automatically.

## Other assumptions

- Truck capacity is expressed in FIN pallet units.
- An order assigned to a driver without a defined capacity gets a warning.
- Saved plans persist in SQLite on the backend (`data/plans.db`). A local browser
  draft is also kept automatically in `localStorage`.
- This is a customer demo, not production software.

## Future AI extension ideas

- **Excel intelligence:** ML-assisted column mapping and data cleaning for any
  customer spreadsheet format.
- **Demand forecasting:** predict daily volumes per route from history.
- **Delivery time windows:** ETA prediction and time-window aware planning.
- **Natural language interface:** "Move all Nokia orders to Driver B" style
  commands on top of the structured plan.
- **Time windows and driving-time limits:** delivery windows, driver hours,
  multi-day routes.
