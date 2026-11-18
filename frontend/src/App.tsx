import { useEffect, useState } from "react";
import {
  applyAddressBook,
  calculatePlan,
  exportDriverSheets,
  geocodeOrders,
  optimizeRoutes,
  optimizeStopOrder,
} from "./api/client";
import FileUpload from "./components/FileUpload";
import OrderTable from "./components/OrderTable";
import RouteSummary from "./components/RouteSummary";
import DriverPlan from "./components/DriverPlan";
import Toolbar from "./components/Toolbar";
import PlanDatePicker from "./components/PlanDatePicker";
import OptimizationPreview from "./components/OptimizationPreview";
import StopOptimizationPreview from "./components/StopOptimizationPreview";
import RouteMap from "./components/RouteMap";
import SavedPlansPanel from "./components/SavedPlansPanel";
import AddressBookPanel from "./components/AddressBookPanel";
import type {
  DriverCapacity,
  OptimizeResponse,
  Order,
  RouteSummary as RouteSummaryType,
  SavedPlan,
  StopOptimizeResponse,
} from "./types/dispatch";
import { addDays, formatPlanDateFi, todayIso } from "./utils/date";
import { clearDraft, formatDraftTime, loadDraft, saveDraft } from "./utils/planDraft";
import { finEquivalent } from "./utils/pallet";
import { mergeLocation, withOrderDefaults } from "./utils/order";

const DEFAULT_DRIVERS: DriverCapacity[] = [
  { driverName: "Driver A", truckCapacity: 48 },
  { driverName: "Driver B", truckCapacity: 44 },
  { driverName: "Driver C", truckCapacity: 40 },
];

function defaultPlanName(planDate: string): string {
  return `Plan ${formatPlanDateFi(planDate)}`;
}

export default function App() {
  const [orders, setOrders] = useState<Order[]>([]);
  const [planDate, setPlanDate] = useState(todayIso);
  const [drivers, setDrivers] = useState<DriverCapacity[]>(DEFAULT_DRIVERS);
  const [summaries, setSummaries] = useState<RouteSummaryType[]>([]);
  const [activePlanId, setActivePlanId] = useState<string | null>(null);
  const [planName, setPlanName] = useState("");
  const [draftBanner, setDraftBanner] = useState<{ savedAt: string } | null>(null);
  const [newDriverName, setNewDriverName] = useState("");
  const [newDriverCapacity, setNewDriverCapacity] = useState(40);
  const [calculating, setCalculating] = useState(false);
  const [optimizing, setOptimizing] = useState(false);
  const [optimizingStops, setOptimizingStops] = useState(false);
  const [exporting, setExporting] = useState(false);
  const [geocoding, setGeocoding] = useState(false);
  const [applyingOptimization, setApplyingOptimization] = useState(false);
  const [optimizeAll, setOptimizeAll] = useState(false);
  const [routePreview, setRoutePreview] = useState<OptimizeResponse | null>(null);
  const [stopPreview, setStopPreview] = useState<StopOptimizeResponse | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  useEffect(() => {
    const draft = loadDraft();
    if (draft && (draft.orders.length > 0 || draft.activePlanId)) {
      setDraftBanner({ savedAt: draft.savedAt });
    }
  }, []);

  useEffect(() => {
    const timer = window.setTimeout(() => {
      saveDraft({
        planDate,
        orders,
        drivers,
        activePlanId,
        activePlanName: planName,
        savedAt: new Date().toISOString(),
      });
    }, 800);
    return () => window.clearTimeout(timer);
  }, [planDate, orders, drivers, activePlanId, planName]);

  function resetWorkflowState() {
    setSummaries([]);
    setRoutePreview(null);
    setStopPreview(null);
  }

  function handleOrdersLoaded(loaded: Order[]) {
    const normalized = loaded.map(withOrderDefaults);
    setOrders(normalized);
    setActivePlanId(null);
    setPlanName(defaultPlanName(planDate));
    resetWorkflowState();
    setMessage(null);
    // Auto-locate right after import when any order has an address
    // (from the sheet, the consignee cell or the address register).
    if (normalized.some((o) => o.address.trim())) {
      handleGeocode(normalized);
    }
  }

  function handleOrdersChange(updated: Order[]) {
    setOrders(
      updated.map((o) => ({
        ...o,
        finEquivalent: finEquivalent(o.pallets, o.palletType, o.stackable),
      }))
    );
  }

  function handleClearAllOrders() {
    if (orders.length === 0) return;
    if (!window.confirm(`Remove all ${orders.length} orders from the current plan?`)) return;
    setOrders([]);
    resetWorkflowState();
    setMessage("All orders removed.");
  }

  function handleActivePlanDeleted() {
    setOrders([]);
    setDrivers(DEFAULT_DRIVERS);
    setPlanDate(todayIso);
    setActivePlanId(null);
    setPlanName("");
    resetWorkflowState();
  }

  function handleNewPlan() {
    if (
      orders.length > 0 &&
      !window.confirm("Start a new empty plan? Unsaved changes remain in the browser draft.")
    ) {
      return;
    }
    setOrders([]);
    setDrivers(DEFAULT_DRIVERS);
    setPlanDate(todayIso);
    setActivePlanId(null);
    setPlanName("");
    resetWorkflowState();
    setMessage("New plan started.");
  }

  function handlePlanLoaded(plan: SavedPlan) {
    setOrders(plan.orders.map(withOrderDefaults));
    setDrivers(plan.drivers.length > 0 ? plan.drivers : DEFAULT_DRIVERS);
    setPlanDate(plan.planDate);
    setActivePlanId(plan.id);
    setPlanName(plan.name);
    resetWorkflowState();
    setDraftBanner(null);
  }

  function handlePlanSaved(plan: SavedPlan) {
    setActivePlanId(plan.id);
    setPlanName(plan.name);
  }

  function restoreDraft() {
    const draft = loadDraft();
    if (!draft) return;
    setOrders(draft.orders.map(withOrderDefaults));
    setDrivers(draft.drivers.length > 0 ? draft.drivers : DEFAULT_DRIVERS);
    setPlanDate(draft.planDate);
    setActivePlanId(draft.activePlanId);
    setPlanName(draft.activePlanName);
    resetWorkflowState();
    setDraftBanner(null);
    setMessage(`Restored local draft from ${formatDraftTime(draft.savedAt)}.`);
  }

  function dismissDraft() {
    clearDraft();
    setDraftBanner(null);
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

  /** Merge geocoded/filled addresses into current orders without losing edits made meanwhile. */
  function mergeLocated(located: Order[]) {
    const byId = new Map(located.map((o) => [o.id, o]));
    setOrders((current) =>
      current.map((o) => {
        const match = byId.get(o.id);
        return match ? mergeLocation(o, match) : o;
      })
    );
  }

  async function handleGeocode(source: Order[] = orders) {
    setGeocoding(true);
    setStopPreview(null);
    setMessage("Locating addresses…");
    try {
      let working = source;
      let lastPending = Number.POSITIVE_INFINITY;
      // The server geocodes a limited batch per call (geocoder rate limit);
      // keep calling while it makes progress.
      for (let round = 0; round < 100; round += 1) {
        const result = await geocodeOrders(working);
        working = result.orders;
        mergeLocated(result.orders);
        const withoutAddress = result.orders.filter((o) => !o.address.trim()).length;
        if (result.pending === 0 || result.pending >= lastPending) {
          const parts = [
            `Located ${result.located} order(s) by address/postal code.`,
            result.failed > 0 ? `${result.failed} address(es) not found.` : "",
            result.pending > 0 ? `${result.pending} still pending — try again later.` : "",
            withoutAddress > 0
              ? `${withoutAddress} order(s) without address use the route area centre.`
              : "",
            ...result.notes,
          ];
          setMessage(parts.filter(Boolean).join(" "));
          break;
        }
        lastPending = result.pending;
        setMessage(
          `Locating addresses… ${result.located} located, ${result.pending} remaining (about 1 per second).`
        );
      }
    } catch (err) {
      setMessage(`Locating addresses failed: ${(err as Error).message}`);
    } finally {
      setGeocoding(false);
    }
  }

  async function handleApplyAddressBook() {
    const before = orders.filter((o) => o.address.trim()).length;
    const updated = await applyAddressBook(orders);
    mergeLocated(updated);
    const filled = updated.filter((o) => o.address.trim()).length - before;
    setMessage(
      filled > 0
        ? `Filled ${filled} address(es) from the register. Press "Locate addresses" to place them on the map.`
        : "No missing addresses matched the register."
    );
  }

  async function handleOptimize() {
    setOptimizing(true);
    setMessage(null);
    setRoutePreview(null);
    setStopPreview(null);
    try {
      const result = await optimizeRoutes(
        orders,
        drivers,
        optimizeAll ? "all" : "unassigned_only"
      );
      setRoutePreview(result);
      setMessage(
        result.changes.length > 0
          ? `Route optimization ready: ${result.changes.length} change(s) to review.`
          : "Route optimization found no changes to apply."
      );
    } catch (err) {
      setMessage(`Route optimization failed: ${(err as Error).message}`);
    } finally {
      setOptimizing(false);
    }
  }

  async function handleOptimizeStops() {
    setOptimizingStops(true);
    setMessage(null);
    setStopPreview(null);
    setRoutePreview(null);
    try {
      const result = await optimizeStopOrder(orders, drivers);
      setStopPreview(result);
      setMessage(
        result.changes.length > 0
          ? `Stop order ready: ${result.changes.length} sequence change(s) to review.`
          : "Stop order optimization found no changes to apply."
      );
    } catch (err) {
      setMessage(`Stop order optimization failed: ${(err as Error).message}`);
    } finally {
      setOptimizingStops(false);
    }
  }

  async function applyRoutePreview(runCalculate: boolean) {
    if (!routePreview) return;
    setApplyingOptimization(true);
    setMessage(null);
    try {
      const changeIds = new Set(routePreview.changes.map((c) => c.orderId));
      const suggestedById = new Map(
        routePreview.orders.map((order) => [order.id, order.deliveryDriver])
      );
      const updatedOrders = orders.map((order) =>
        changeIds.has(order.id)
          ? {
              ...order,
              deliveryDriver: suggestedById.get(order.id) ?? order.deliveryDriver,
              // Moved to another truck: its old stop number no longer applies.
              stopSequence: null,
            }
          : order
      );
      setOrders(updatedOrders);
      setRoutePreview(null);

      if (runCalculate) {
        const result = await calculatePlan(updatedOrders, drivers);
        setOrders(result.orders);
        setSummaries(result.routeSummaries);
        const overloaded = result.routeSummaries.filter((s) => s.overloaded);
        setMessage(
          overloaded.length > 0
            ? `Optimization applied and calculated. ${overloaded.length} route(s) overloaded.`
            : "Optimization applied and calculated. All routes within capacity."
        );
      } else {
        setSummaries(routePreview.routeSummaries);
        setMessage("Route optimization applied.");
      }
    } catch (err) {
      setMessage(`Apply failed: ${(err as Error).message}`);
    } finally {
      setApplyingOptimization(false);
    }
  }

  function applyStopPreview() {
    if (!stopPreview) return;
    setApplyingOptimization(true);
    setMessage(null);
    try {
      const sequenceById = new Map(
        stopPreview.orders.map((order) => [order.id, order.stopSequence ?? null])
      );
      setOrders(
        orders.map((order) => ({
          ...order,
          stopSequence: sequenceById.get(order.id) ?? order.stopSequence ?? null,
        }))
      );
      setSummaries(stopPreview.routeSummaries);
      setStopPreview(null);
      setMessage("Stop order applied.");
    } finally {
      setApplyingOptimization(false);
    }
  }

  function handleNextDay() {
    const delivered = orders.filter((o) => o.status === "DELIVERED").length;
    const kept = orders.filter((o) => o.status !== "DELIVERED");
    const nextDate = addDays(planDate, 1);
    setOrders(kept);
    setPlanDate(nextDate);
    resetWorkflowState();
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
    const assigned = orders.filter((o) => o.deliveryDriver.trim() === name).length;
    if (
      assigned > 0 &&
      !window.confirm(
        `Remove driver "${name}"? ${assigned} order(s) are assigned to this driver (they will keep the name but show a capacity warning).`
      )
    ) {
      return;
    }
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
        {draftBanner && (
          <div className="draft-banner">
            <span>
              Unsaved local draft from {formatDraftTime(draftBanner.savedAt)} is available.
            </span>
            <div className="draft-banner-actions">
              <button type="button" className="btn-primary" onClick={restoreDraft}>
                Restore draft
              </button>
              <button type="button" onClick={dismissDraft}>
                Dismiss
              </button>
            </div>
          </div>
        )}

        <FileUpload onOrdersLoaded={handleOrdersLoaded} />

        <SavedPlansPanel
          planDate={planDate}
          orders={orders}
          drivers={drivers}
          activePlanId={activePlanId}
          planName={planName}
          onPlanNameChange={setPlanName}
          onPlanLoaded={handlePlanLoaded}
          onPlanSaved={handlePlanSaved}
          onNewPlan={handleNewPlan}
          onActivePlanDeleted={handleActivePlanDeleted}
          onMessage={setMessage}
        />

        <PlanDatePicker planDate={planDate} onChange={setPlanDate} />

        <Toolbar
          onCalculate={handleCalculate}
          onOptimize={handleOptimize}
          onOptimizeStops={handleOptimizeStops}
          onNextDay={handleNextDay}
          onExport={handleExport}
          onGeocode={() => handleGeocode()}
          geocoding={geocoding}
          calculating={calculating}
          optimizing={optimizing}
          optimizingStops={optimizingStops}
          exporting={exporting}
          hasOrders={orders.length > 0}
          optimizeAll={optimizeAll}
          onOptimizeAllChange={setOptimizeAll}
        />
        {message && <p className="message-banner">{message}</p>}

        {routePreview && (
          <OptimizationPreview
            title="Route optimization preview"
            changes={routePreview.changes}
            notes={routePreview.notes}
            onApply={() => applyRoutePreview(false)}
            onApplyAndCalculate={() => applyRoutePreview(true)}
            onDismiss={() => setRoutePreview(null)}
            applying={applyingOptimization}
          />
        )}

        {stopPreview && (
          <StopOptimizationPreview
            changes={stopPreview.changes}
            notes={stopPreview.notes}
            onApply={applyStopPreview}
            onDismiss={() => setStopPreview(null)}
            applying={applyingOptimization}
          />
        )}

        <OrderTable
          orders={orders}
          drivers={drivers}
          onChange={handleOrdersChange}
          onClearAll={handleClearAllOrders}
        />

        <AddressBookPanel
          orders={orders}
          onApplyToPlan={handleApplyAddressBook}
          onMessage={setMessage}
        />

        <section className="card">
          <h2>3. Drivers &amp; truck capacities (FIN units)</h2>
          <p className="status-text">
            Capacity is shown next to each driver name, e.g. Driver A (48). Change the
            number to match the truck that driver uses.
          </p>
          <div className="driver-settings">
            {drivers.map((d) => (
              <div key={d.driverName} className="driver-row">
                <span className="driver-name">
                  {d.driverName}{" "}
                  <span className="driver-capacity-tag">({d.truckCapacity})</span>
                </span>
                <label className="driver-capacity-field">
                  <span className="muted">Capacity</span>
                  <input
                    type="number"
                    min={0}
                    className="input-narrow"
                    value={d.truckCapacity}
                    onChange={(e) =>
                      updateCapacity(d.driverName, Number(e.target.value) || 0)
                    }
                  />
                </label>
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
                title="Truck capacity (FIN)"
                value={newDriverCapacity}
                onChange={(e) => setNewDriverCapacity(Number(e.target.value) || 0)}
              />
              <button onClick={addDriver}>+ Add driver</button>
            </div>
          </div>
        </section>

        <RouteSummary summaries={summaries} />

        <RouteMap orders={orders} />

        <DriverPlan
          orders={orders}
          drivers={drivers}
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
