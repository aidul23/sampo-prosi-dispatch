import { useState } from "react";
import { calculatePlan, exportDriverSheets } from "./api/client";
import FileUpload from "./components/FileUpload";
import OrderTable from "./components/OrderTable";
import RouteSummary from "./components/RouteSummary";
import DriverPlan from "./components/DriverPlan";
import Toolbar from "./components/Toolbar";
import PlanDatePicker from "./components/PlanDatePicker";
import type {
  DriverCapacity,
  Order,
  RouteSummary as RouteSummaryType,
} from "./types/dispatch";
import { addDays, formatPlanDateFi, todayIso } from "./utils/date";
import { finEquivalent } from "./utils/pallet";

const DEFAULT_DRIVERS: DriverCapacity[] = [
  { driverName: "Driver A", truckCapacity: 48 },
  { driverName: "Driver B", truckCapacity: 44 },
  { driverName: "Driver C", truckCapacity: 40 },
];

export default function App() {
  const [orders, setOrders] = useState<Order[]>([]);
  const [planDate, setPlanDate] = useState(todayIso);
  const [drivers, setDrivers] = useState<DriverCapacity[]>(DEFAULT_DRIVERS);
  const [summaries, setSummaries] = useState<RouteSummaryType[]>([]);
  const [newDriverName, setNewDriverName] = useState("");
  const [newDriverCapacity, setNewDriverCapacity] = useState(40);
  const [calculating, setCalculating] = useState(false);
  const [exporting, setExporting] = useState(false);
  const [message, setMessage] = useState<string | null>(null);

  function handleOrdersLoaded(loaded: Order[]) {
    setOrders(loaded);
    setSummaries([]);
    setMessage(null);
  }

  // Keep FIN equivalents live while editing; warnings refresh on "Calculate plan".
  function handleOrdersChange(updated: Order[]) {
    setOrders(
      updated.map((o) => ({
        ...o,
        finEquivalent: finEquivalent(o.pallets, o.palletType, o.stackable),
      }))
    );
  }

  async function handleCalculate() {
    setCalculating(true);
    setMessage(null);
    try {
      const result = await calculatePlan(orders, drivers);
      setOrders(result.orders);
      setSummaries(result.routeSummaries);
      const overloaded = result.routeSummaries.filter((s) => s.overloaded);
      setMessage(
        overloaded.length > 0
          ? `Plan calculated. ${overloaded.length} route(s) overloaded: ${overloaded
              .map((s) => s.driverName)
              .join(", ")}`
          : "Plan calculated. All routes within capacity."
      );
    } catch (err) {
      setMessage(`Calculation failed: ${(err as Error).message}`);
    } finally {
      setCalculating(false);
    }
  }

  function handleNextDay() {
    const delivered = orders.filter((o) => o.status === "DELIVERED").length;
    const kept = orders.filter((o) => o.status !== "DELIVERED");
    const nextDate = addDays(planDate, 1);
    setOrders(kept);
    setPlanDate(nextDate);
    setSummaries([]);
    setMessage(
      `Next day plan created for ${formatPlanDateFi(nextDate)}: removed ${delivered} delivered order(s), kept ${kept.length} (incl. carry-overs).`
    );
  }

  async function handleExport() {
    setExporting(true);
    setMessage(null);
    try {
      await exportDriverSheets(orders, drivers, planDate);
      setMessage(`Driver sheets exported for ${formatPlanDateFi(planDate)}.`);
    } catch (err) {
      setMessage(`Export failed: ${(err as Error).message}`);
    } finally {
      setExporting(false);
    }
  }

  function addDriver() {
    const name = newDriverName.trim();
    if (!name || drivers.some((d) => d.driverName === name)) return;
    setDrivers([...drivers, { driverName: name, truckCapacity: newDriverCapacity }]);
    setNewDriverName("");
  }

  function removeDriver(name: string) {
    setDrivers(drivers.filter((d) => d.driverName !== name));
  }

  function updateCapacity(name: string, capacity: number) {
    setDrivers(
      drivers.map((d) =>
        d.driverName === name ? { ...d, truckCapacity: capacity } : d
      )
    );
  }

  return (
    <div className="app">
      <header className="app-header">
        <h1>Sampo Dispatch Planning Demo</h1>
        <p>From daily Excel sheet to structured dispatch planning</p>
        <p className="plan-date-banner">{formatPlanDateFi(planDate)}</p>
      </header>

      <main>
        <FileUpload onOrdersLoaded={handleOrdersLoaded} />

        <PlanDatePicker planDate={planDate} onChange={setPlanDate} />

        <Toolbar
          onCalculate={handleCalculate}
          onNextDay={handleNextDay}
          onExport={handleExport}
          calculating={calculating}
          exporting={exporting}
          hasOrders={orders.length > 0}
        />
        {message && <p className="message-banner">{message}</p>}

        <OrderTable
          orders={orders}
          driverNames={drivers.map((d) => d.driverName)}
          onChange={handleOrdersChange}
        />

        <section className="card">
          <h2>3. Drivers &amp; truck capacities (FIN units)</h2>
          <div className="driver-settings">
            {drivers.map((d) => (
              <div key={d.driverName} className="driver-row">
                <span className="driver-name">{d.driverName}</span>
                <input
                  type="number"
                  min={0}
                  className="input-narrow"
                  value={d.truckCapacity}
                  onChange={(e) =>
                    updateCapacity(d.driverName, Number(e.target.value) || 0)
                  }
                />
                <button
                  type="button"
                  className="btn-remove"
                  title="Remove driver"
                  aria-label="Remove driver"
                  onClick={() => removeDriver(d.driverName)}
                >
                  ×
                </button>
              </div>
            ))}
            <div className="driver-row driver-row-new">
              <input
                type="text"
                placeholder="New driver name"
                value={newDriverName}
                onChange={(e) => setNewDriverName(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && addDriver()}
              />
              <input
                type="number"
                min={0}
                className="input-narrow"
                value={newDriverCapacity}
                onChange={(e) => setNewDriverCapacity(Number(e.target.value) || 0)}
              />
              <button onClick={addDriver}>+ Add driver</button>
            </div>
          </div>
        </section>

        <RouteSummary summaries={summaries} />

        <DriverPlan
          orders={orders}
          planDateLabel={formatPlanDateFi(planDate)}
          onExport={handleExport}
          exporting={exporting}
        />
      </main>

      <footer className="app-footer">
        Rule-based demo — no AI yet. Built to mirror the current Excel workflow.
      </footer>
    </div>
  );
}
