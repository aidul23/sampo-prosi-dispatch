import type { Order } from "../types/dispatch";

interface Props {
  orders: Order[];
  planDateLabel: string;
  onExport: () => void;
  exporting: boolean;
}

export default function DriverPlan({ orders, planDateLabel, onExport, exporting }: Props) {
  const drivers = Array.from(
    new Set(orders.map((o) => o.deliveryDriver.trim()).filter(Boolean))
  ).sort();
  const unassigned = orders.filter((o) => !o.deliveryDriver.trim());

  function section(title: string, driverOrders: Order[]) {
    const total = driverOrders.reduce((sum, o) => sum + o.finEquivalent, 0);
    return (
      <div key={title} className="driver-section">
        <h3>
          {title}{" "}
          <span className="muted">
            ({driverOrders.length} orders, {total.toFixed(1)} FIN)
          </span>
        </h3>
        <div className="table-wrap">
          <table className="driver-plan-table">
            <thead>
              <tr>
                <th>Consignee</th>
                <th>Customer</th>
                <th className="col-num">Pallets</th>
                <th className="col-num">FIN Eq.</th>
                <th>Route Area</th>
                <th>Extra Info</th>
              </tr>
            </thead>
            <tbody>
              {driverOrders.map((o) => (
                <tr key={o.id}>
                  <td>{o.consignee || "—"}</td>
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
          {drivers.map((driver) =>
            section(
              driver,
              orders.filter((o) => o.deliveryDriver.trim() === driver)
            )
          )}
          {unassigned.length > 0 && section("Unassigned", unassigned)}
        </>
      )}
    </section>
  );
}
