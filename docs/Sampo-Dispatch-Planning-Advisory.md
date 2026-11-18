# Sampo Dispatch Planning — Advisory Overview

**Prepared for:** Customer review (outgoing goods planning)  
**Status:** Working demonstration / advisory pilot  
**Purpose:** Explain what the system does today, how each step works, and how we will extend it based on your feedback.

---

## 1. Purpose of this document

You currently plan daily outgoing deliveries in Excel. This document describes a web-based planning demo built around that workflow.

It is intended as:

- An **explanation** of the process end-to-end  
- An **advisory** on what is automatic vs. what remains under your control  
- A **basis for discussion** — further requirements will be implemented according to your real daily needs  

This is **not** an AI black box. Planning rules are transparent and can be adjusted with you.

---

## 2. Your current workflow (as we understand it)

Outgoing goods are loaded at your terminal in **Pohjanmaa (Kristiinankaupunki)** and delivered around Finland.

Your daily Excel sheet typically includes:

| Column | Content | Role in planning |
|--------|---------|------------------|
| **A** | Customer | Who the order belongs to (often recurring) |
| **B** | Pickup driver | Driver who brings goods to the terminal |
| **C** | Consignee (Vastaanottaja) | Delivery destination / receiver |
| **D** | Number of pallets (FIN) | Load size already converted to FIN pallet units |
| **E** | Extra information | Notes (codes, special instructions, etc.) |
| **F** | Delivery driver | Who takes the order on their load and delivers it |

**Manual work today (typical):**

1. Maintain the order list  
2. Know truck capacities in FIN units  
3. Assign delivery drivers (column F) by experience and geography  
4. Check that loads do not exceed capacity  
5. Produce driver-specific lists  

Our demo aims to support these steps — not replace your judgment.

---

## 3. What we built — high-level process

```
Excel sheet
    → Import into the planning tool
    → Edit / correct orders if needed
    → Set drivers and truck capacities
    → Calculate capacity (warnings if overloaded)
    → Optional: Optimize driver assignment
    → Optional: Optimize stop order within each route
    → View approximate map
    → Export driver sheets back to Excel
    → Save / load / update / delete plans
```

You remain in control: optimization only **suggests**; you **review and apply**.

---

## 4. Step-by-step: what happens and how

### 4.1 Load orders (Excel import)

**What you do:** Upload your daily Excel file (or use sample data for a demo).

**What the system does:**

- Detects the header row (even if there are title/date rows above it)  
- Maps columns A–F (and Finnish headers such as Asiakas, Vastaanottaja, Lavat, Kuski)  
- Supports grouped customers (empty customer cell inherited from the row above)  
- Treats pallet numbers as **FIN units** (matching your current practice)  
- If there is no separate “route area” column, the system **infers a delivery area** from the consignee text  
  - Examples: `Valio Espoo` → Espoo · `Lidl Laukaa` → Laukaa · `Vantaa-Helsinki` → Vantaa  
  - Unrecognised names → “Unspecified” (you can correct manually)

**Your control:** Every field can still be edited in the table after import.

---

### 4.2 Edit the daily plan

**What you do:** Correct consignments, pallets, drivers, areas, status, and notes.

**What the system supports:**

- Add / edit / delete individual orders  
- Clear all orders (with confirmation)  
- Add / edit / remove delivery drivers and their truck capacities (FIN)  
- Set the plan date  
- Mark order status (e.g. NEW, PLANNED, DELIVERED, CARRY_OVER)

This mirrors working in Excel, with clearer capacity feedback.

---

### 4.3 Calculate plan (capacity check)

**What you do:** Press **Calculate plan**.

**What the system does:**

- Recalculates FIN load per order (supports FIN / EUR / OTHER and optional stackable logic if used)  
- Sums load per delivery driver  
- Compares against each truck’s FIN capacity  
- Shows remaining capacity and **overload warnings**

**Important:** This step does **not** change who drives what. It only checks the current assignments.

---

### 4.4 Optimize routes (driver assignment)

**What you do:** Press **Optimize routes**, review the preview, then Apply (or Apply & calculate).

**What we use:** Transparent routing rules based on real road distances (not AI).

**Logic in short:**

1. Each order is placed on the map (exact address, postal code, or area centre)  
2. Trucks start in different regions, so routes cover different directions  
3. Each remaining order goes to the truck where it adds the fewest kilometres, within FIN capacity  
4. Orders are then moved or swapped between trucks while that shortens total driving  
5. Very long routes (over ~900 km round trip, adjustable) are avoided — far-apart regions are not combined on one truck  
6. Orders with no known location, and orders that do not fit any truck, stay unassigned with a note  

Every suggestion shows why, e.g. *"Adds ~35 km to Driver B's route (Driver A would add ~210 km)"*, and each truck's load and estimated kilometres.

**Modes:**

- **Default:** Only fill **unassigned** orders (your existing column F choices stay)  
- **Optional:** Re-optimize **all** assignments (you must choose this explicitly)

**Your control:** Preview of every change before apply; you can dismiss or edit manually afterward.

---

### 4.5 Optimize stop order (delivery sequence)

**What you do:** After drivers are assigned, press **Optimize stop order**, review, then Apply.

**What we use:** Shortest round trip from the terminal and back, using road distances between delivery addresses (approximate distances when no address is known).

**Logic in short:**

1. For each delivery driver, start from the terminal  
2. Build a tour by always going to the closest next stop, then improve it by reversing / moving stops while the round trip gets shorter  
3. Write a **Stop #** on each order for that driver  

**Current limitation (advisory):**  
Depot and distances are approximate (area-level). They are suitable for planning discussion, not street-level navigation. Depot location can be aligned to **Kristiinankaupunki** (or your real terminal) based on your confirmation.

---

### 4.5b Delivery addresses (more accurate map and stop order)

**What you do:** Optionally give orders a delivery address — in a new Excel column (e.g. G "Osoite"), inside the consignee cell (e.g. *Valio, Tuupakantie 10, 01740 Vantaa*), by typing it in the table, or once in the **Address register** for recurring consignees. Then press **Locate addresses**.

**What the system does:**

- Finds the street address / postal code in the text and looks it up on OpenStreetMap  
- Falls back to the postal code area if the street is not found, and to the delivery area centre if there is no address  
- Shows the precision per order (green = address, yellow = postal code, grey = area)  
- Fills missing addresses automatically from the address register  
- Uses **real road distances** when optimizing stop order  

**Your control:** Addresses are optional and editable; orders without an address work exactly as before.

---

### 4.6 Route map

**What you see:** An OpenStreetMap view with:

- Pins coloured by delivery driver  
- Approximate positions based on delivery area centres  
- Optional dashed lines showing stop sequence from the depot  

**What it is for:** Visual understanding of the day’s plan.  
**What it is not:** Live tracking or turn-by-turn routing.

---

### 4.7 Export driver sheets

**What you do:** Press **Export driver sheets**.

**What you get:** An Excel workbook with:

- Full plan  
- One sheet per delivery driver (including Stop # when sequenced)  
- Unassigned orders (if any)  
- Route capacity summary  

This keeps your existing Excel-based sharing habit for drivers / office.

---

### 4.8 Save, update, load, delete

**What you can do:**

| Action | Meaning |
|--------|---------|
| **Save as new** | Store the current plan on the server with a name and date |
| **Update saved plan** | Overwrite the plan you currently have open |
| **Load** | Open a previously saved plan |
| **Delete** | Remove a saved plan (with confirmation) |
| **New plan** | Start empty |
| **Local draft** | Browser automatically keeps a backup if you refresh by mistake |

**Advisory note:** The demo storage is suitable for evaluation. For long-term daily production use we can strengthen persistence and access control according to your requirements.

---

### 4.9 Next-day planning

**What you do:** Press **Create next day plan**.

**What the system does:**

- Advances the plan date by one day  
- Removes orders marked **DELIVERED**  
- Keeps remaining / carry-over orders for the next day  

We will refine this to match your real next-day practice once you confirm it.

---

## 5. What is automatic vs. what stays manual

| Task | System support | Your role |
|------|----------------|-----------|
| Reading Excel A–F | Automatic import | Check / correct |
| FIN capacity check | Automatic | Decide how to fix overloads |
| Driver assignment | Optional suggestion | Approve / override |
| Delivery sequence | Optional suggestion | Approve / override |
| Map overview | Automatic (approx.) | Interpret |
| Driver Excel export | Automatic | Share / print as needed |
| Final decision | — | Always yours |

---

## 6. Technology approach (plain language)

| Topic | Approach |
|-------|----------|
| Planning method | Transparent **rules** (area + capacity + sequence) |
| Maps | OpenStreetMap (visual only) |
| AI / machine learning | **Not used** in this demo |
| Live GPS / traffic | **Not used** |
| Data | Excel import/export + saveable plans |

We chose this approach so you can understand and trust every suggestion — and so we can change rules quickly when you describe real constraints.

---

## 7. Known assumptions and limitations (honest status)

1. Depot is set to your terminal: **Porintie 382, Lapväärtti** (map + stop sequencing).  
2. **Consignee text** is sometimes incomplete (names only, phone numbers, codes). Area parsing is approximate and editable.  
3. **Distances** are road distances between addresses when addresses are given; otherwise area-level approximations. Stop order is a simple "nearest next stop" rule, not a full route optimization.  
4. **Pickup drivers** (column B) are stored but not yet used in optimization logic.  
5. This is a **demo / advisory pilot**, not a finished production system with logins, audits, or SLA guarantees.  

These are not blockers for evaluation — they are the natural next refinement topics.

---

## 8. How we recommend using the demo together

**Suggested evaluation flow:**

1. Upload one real daily Excel sheet  
2. Check that customers, consignments, and FIN numbers look correct  
3. Enter your real drivers and truck capacities  
4. Calculate plan — review overload warnings  
5. Try Optimize routes (unassigned only first) — review preview carefully  
6. Optionally optimize stop order and look at the map  
7. Export driver sheets and compare with your current method  
8. Tell us what is wrong, missing, or must never change  

Your feedback becomes the requirement list for the next version.

---

## 9. Questions we need from you (to finalize the next version)

Please help us confirm:

1. **Daily scenario** — step by step, what do you do from morning until the plan is ready?  
2. **Depot / terminal** — confirm Kristiinankaupunki (or other) as the start point.  
3. **Truck capacities** — FIN capacity per truck / driver on a typical day.  
4. **How many delivery drivers** and whether routes are usually fixed by region.  
5. Is column **D always already FIN**, or sometimes raw pallet counts?  
6. Should **pickup drivers (B)** influence delivery planning, or only delivery drivers (F)?  
7. What happens to unfinished orders the next day?  
8. Who receives the final plan — only the planner, or also drivers (print / Excel / phone)?  
9. Any hard rules (e.g. cold chain, time windows, “this customer always same driver”)?
9b. How long may one truck's route be — one day (km or driving hours), or are some routes overnight / two-day?  
10. Is a Finnish-language interface needed for daily use?

---

## 10. Proposed next steps (after your feedback)

| Priority | Item |
|----------|------|
| High | Align depot to your real terminal |
| High | Tune area recognition with your real consignee names |
| High | Configure real drivers and capacities |
| Medium | Adjust next-day / carry-over rules to match your practice |
| Medium | Finnish UI labels if required |
| Later | Stronger production storage, user access, street-level routing if needed |

**Principle:** Further requirements will be served according to your operational needs — we will not add complexity you do not ask for.

---

## 11. Summary for decision-makers

- We mirrored your Excel outgoing-goods process in a web tool.  
- Capacity checking and optional route/stop suggestions reduce manual calculation.  
- You keep approval and override control.  
- Export returns Excel driver lists you can still use.  
- The next version should be shaped by your real daily scenario and constraints.  

---

## 12. Contact / follow-up

Please review this advisory with a real daily sheet when possible.  
After the meeting, we will update the demo according to the answers above and share a short refined scenario for your confirmation.

---

*Document version: Advisory demo overview — for customer discussion*  
*System type: Rule-based dispatch planning demonstration*
