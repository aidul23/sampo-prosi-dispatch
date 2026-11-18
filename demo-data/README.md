# Demo dataset

`sampo-demo-orders-2026-11-19.xlsx` — a fictional daily outgoing-goods sheet
in the same layout as the customer's Excel (date title row, Finnish headers,
unnamed columns B and E, customer written once per group). Company names are
fictional; street addresses are real public streets so geocoding works.

| | |
|---|---|
| Orders | 30 from 6 shipper customers |
| Pallets | 121 FIN (default trucks: 48 + 44 + 40 = 132) |
| Pre-assigned | 7 orders on Driver A / B / C (column F "Kuski"), 23 unassigned |

## What each part demonstrates

| Case | Example rows | Expected result |
|---|---|---|
| Address in the new **Osoite** column (G) | Valio Vantaa, Kesko Oulu | 🟢 exact address |
| Address written **inside the consignee cell** | `S-Market Sörnäinen, Hämeentie 13, 00530 Helsinki` | address extracted, 🟢 |
| **Postal code only** | Tokmanni Nokia (`37100 Nokia`), Prisma Kokkola | 🟡 postal code area |
| Street not found → postal fallback | Ravintola Kappeli (Eteläesplanadi 1) | 🟡 postal code area |
| **No address** | Kahvila Kangasala, Garden Center Kouvola | ⚪ route area centre |
| Area from **postal city** when the name has none | Ravintola Hovioikeus → Vaasa | route area filled from address |
| Phone numbers / door codes in consignee | `… p. 040 123 4567`, `ovikoodi 1234` | ignored |
| **Unrecognised consignee** | `Tuntematon vastaanottaja 040 555 1234` | "Unspecified" + warning |
| Grouped customer rows | customer cell empty under first row | inherited from row above |

## Suggested demo flow (≈5 min)

1. **Load orders** → upload the file. Addresses are located automatically
   (~25 s the first time; instant afterwards thanks to the cache).
2. Show the dots in the **Address** column and the pins on the **Route map**.
3. **Address register** → *Save addresses from current plan*. Add one missing
   address, e.g. `Garden Center Kouvola` → `Kauppalankatu 5, 45100 Kouvola`.
   Next time the sheet is uploaded, that address fills in automatically.
4. **Optimize routes** → review preview → *Apply & calculate*. Show the
   reasons ("Adds ~35 km to Driver B's route…") and the per-truck notes
   (load, round-trip km, main areas). For the cleanest regional split, tick
   *Include already assigned orders* — then each truck gets one direction
   (south-east loop / Tampere–Turku / north coast). Note the unknown
   consignee is left for the planner instead of guessed.
5. **Optimize stop order** → notes show "using road distances, ~N km".
   Apply and show **Stop #** in the driver lists and the map lines.
6. Fix the "Unspecified" row by typing a route area or address.
7. **Export driver sheets** → Excel with one sheet per driver, including addresses.

Tip: to show the "first time" geocoding again, use a fresh server database,
otherwise everything is located instantly from the cache.
