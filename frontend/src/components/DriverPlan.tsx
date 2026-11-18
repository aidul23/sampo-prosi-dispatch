import type { DriverCapacity, Order } from "../types/dispatch";
import { formatDriverLabel } from "../data/areaCentroids";

interface Props {
  orders: Order[];
  drivers: DriverCapacity[];
  planDateLabel: string;
  onExport: () => void;
  exporting: boolean;
}

function sortDriverOrders(driverOrders: Order[]): Order[] {
  return [...driverOrders].sort((a, b) => {
    const seqA = a.stopSequence ?? 9999;
    const seqB = b.stopSequence ?? 9999;
    if (seqA !== seqB) return seqA - seqB;
    return a.consignee.localeCompare(b.consignee);
  });
}

export default function DriverPlan({
  orders,
  drivers,
  planDateLabel,
  onExport,
  exporting,
}: Props) {
  const capacityByName = new Map(drivers.map((d) => [d.driverName, d.truckCapacity]));
  const driverNames = Array.from(
    new Set(orders.map((o) => o.deliveryDriver.trim()).filter(Boolean))
  ).sort();
  const unassigned = orders.filter((o) => !o.deliveryDriver.trim());

  function sectionTitle(driverName: string): string {
    const capacity = capacityByName.get(driverName);
    return capacity != null ? formatDriverLabel(driverName, capacity) : driverName;
  }

  function section(title: string, driverOrders: Order[]) {
    const sorted = sortDriverOrders(driverOrders);
    const total = sorted.reduce((sum, o) => sum + o.finEquivalent, 0);
    return (
      <div key={title} className="driver-section">
        <h3>
          {title}{" "}
          <span className="muted">
            ({sorted.length} orders, {total.toFixed(1)} FIN)
          </span>
        </h3>
        <div className="table-wrap">
          <table className="driver-plan-table">
            <thead>
              <tr>
                <th className="col-num">#</th>
                <th>Consignee</th>
                <th>Address</th>
                <th>Customer</th>
                <th className="col-num">Pallets</th>
                <th className="col-num">FIN Eq.</th>
                <th>Route Area</th>
                <th>Extra Info</th>
              </tr>
            </thead>
            <tbody>
              {sorted.map((o) => (
                <tr key={o.id}>
                  <td className="cell-number">{o.stopSequence ?? "—"}</td>
                  <td>{o.consignee || "—"}</td>
                  <td>{o.address || "—"}</td>
                  <td>{o.customer || "—"}</td>
                  <td className="cell-number">
                    <span className="pallet-count">{o.pallets}</span>
                    <span className="pallet-meta">
                      {o.palletType}
                      {o.stackable ? ", stackable" : ""}
                    </span>
                  </td>
                  <td className="cell-number">{o.finEquivalent.toFixed(1)}</td>
                  <td>{o.routeArea || "—"}</td>
                  <td>{o.extraInfo || "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    );
  }

  return (
    <section className="card">
      <div className="card-header">
        <div>
          <h2>5. Driver delivery lists</h2>
          <p className="status-text plan-section-date">{planDateLabel}</p>
        </div>
        <button onClick={onExport} disabled={exporting || orders.length === 0}>
          {exporting ? "Exporting…" : "Export driver sheets"}
        </button>
      </div>
      {orders.length === 0 ? (
        <p className="status-text">No orders to group yet.</p>
      ) : (
        <>
          {driverNames.map((driver) =>
            section(
              sectionTitle(driver),
              orders.filter((o) => o.deliveryDriver.trim() === driver)
            )
          )}
          {unassigned.length > 0 && section("Unassigned", unassigned)}
        </>
      )}
    </section>
  );
}
