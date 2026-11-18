import type { DriverCapacity, Order, OrderStatus, PalletType } from "../types/dispatch";
import { ORDER_STATUSES, PALLET_TYPES } from "../types/dispatch";
import { formatDriverLabel } from "../data/areaCentroids";
import { PRECISION_LABEL } from "../utils/order";

interface Props {
  orders: Order[];
  drivers: DriverCapacity[];
  onChange: (orders: Order[]) => void;
  onClearAll?: () => void;
}

function newEmptyOrder(): Order {
  return {
    id: `new-${Date.now()}-${Math.floor(Math.random() * 1000)}`,
    customer: "",
    pickupDriver: "",
    consignee: "",
    address: "",
    lat: null,
    lng: null,
    geocodePrecision: null,
    pallets: 0,
    palletType: "FIN",
    stackable: false,
    extraInfo: "",
    deliveryDriver: "",
    routeArea: "",
    status: "NEW",
    finEquivalent: 0,
    warning: null,
  };
}

export default function OrderTable({ orders, drivers, onChange, onClearAll }: Props) {
  const driverNames = drivers.map((d) => d.driverName);
  function update(id: string, patch: Partial<Order>) {
    // A changed address invalidates its map location until it is located again.
    const reset: Partial<Order> =
      "address" in patch ? { lat: null, lng: null, geocodePrecision: null } : {};
    onChange(orders.map((o) => (o.id === id ? { ...o, ...patch, ...reset } : o)));
  }

  function remove(id: string) {
    onChange(orders.filter((o) => o.id !== id));
  }

  return (
    <section className="card">
      <div className="card-header">
        <h2>2. Daily orders ({orders.length})</h2>
        <div className="order-table-actions">
          <button onClick={() => onChange([...orders, newEmptyOrder()])}>
            + Add order
          </button>
          {orders.length > 0 && onClearAll && (
            <button type="button" className="btn-danger-text" onClick={onClearAll}>
              Clear all
            </button>
          )}
        </div>
      </div>
      {orders.length === 0 ? (
        <p className="status-text">No orders loaded. Upload an Excel file or load sample data.</p>
      ) : (
        <>
        <p className="location-legend">
          <span><span className="location-dot location-address" /> Exact address</span>
          <span><span className="location-dot location-postal_code" /> Postal code area</span>
          <span><span className="location-dot location-area" /> Not located — route area centre</span>
        </p>
        <div className="table-wrap">
          <table className="order-table">
            <thead>
              <tr>
                <th className="col-customer">Customer</th>
                <th className="col-pickup">Pickup Driver</th>
                <th className="col-consignee">Consignee</th>
                <th className="col-address">Address</th>
                <th className="col-pallets">Pallets</th>
                <th className="col-type">Pallet Type</th>
                <th className="col-stack">Stackable</th>
                <th className="col-extra">Extra Info</th>
                <th className="col-driver">Delivery Driver</th>
                <th className="col-route">Route Area</th>
                <th className="col-status">Status</th>
                <th className="col-fin">FIN Eq.</th>
                <th className="col-warning">Warning</th>
                <th className="col-action"></th>
              </tr>
            </thead>
            <tbody>
              {orders.map((order) => (
                <tr key={order.id} className={order.warning ? "row-warning" : ""}>
                  <td>
                    <input
                      type="text"
                      className="table-input col-customer"
                      placeholder="Customer"
                      value={order.customer}
                      onChange={(e) => update(order.id, { customer: e.target.value })}
                    />
                  </td>
                  <td>
                    <input
                      type="text"
                      className="table-input col-pickup"
                      placeholder="Pickup driver"
                      value={order.pickupDriver}
                      onChange={(e) => update(order.id, { pickupDriver: e.target.value })}
                    />
                  </td>
                  <td>
                    <input
                      type="text"
                      className="table-input col-consignee"
                      placeholder="Consignee"
                      value={order.consignee}
                      onChange={(e) => update(order.id, { consignee: e.target.value })}
                    />
                  </td>
                  <td>
                    <div className="address-cell">
                      <input
                        type="text"
                        className="table-input col-address"
                        placeholder="Street, postal code city"
                        value={order.address}
                        onChange={(e) => update(order.id, { address: e.target.value })}
                      />
                      <span
                        className={`location-dot location-${order.geocodePrecision ?? "area"}`}
                        title={PRECISION_LABEL[order.geocodePrecision ?? "area"]}
                        aria-label={PRECISION_LABEL[order.geocodePrecision ?? "area"]}
                      />
                    </div>
                  </td>
                  <td>
                    <input
                      type="number"
                      min={0}
                      step={0.1}
                      className="table-input table-input-number col-pallets"
                      value={order.pallets}
                      onChange={(e) =>
                        update(order.id, { pallets: Number(e.target.value) || 0 })
                      }
                    />
                  </td>
                  <td>
                    <select
                      className="table-select col-type"
                      value={order.palletType}
                      onChange={(e) =>
                        update(order.id, { palletType: e.target.value as PalletType })
                      }
                    >
                      {PALLET_TYPES.map((t) => (
                        <option key={t} value={t}>
                          {t}
                        </option>
                      ))}
                    </select>
                  </td>
                  <td className="cell-center">
                    <input
                      type="checkbox"
                      className="table-checkbox"
                      checked={order.stackable}
                      onChange={(e) => update(order.id, { stackable: e.target.checked })}
                    />
                  </td>
                  <td>
                    <input
                      type="text"
                      className="table-input col-extra"
                      placeholder="Extra info"
                      value={order.extraInfo}
                      onChange={(e) => update(order.id, { extraInfo: e.target.value })}
                    />
                  </td>
                  <td>
                    <select
                      className="table-select col-driver"
                      value={order.deliveryDriver}
                      onChange={(e) => update(order.id, { deliveryDriver: e.target.value })}
                    >
                      <option value="">— unassigned —</option>
                      {drivers.map((d) => (
                        <option key={d.driverName} value={d.driverName}>
                          {formatDriverLabel(d.driverName, d.truckCapacity)}
                        </option>
                      ))}
                      {order.deliveryDriver &&
                        !driverNames.includes(order.deliveryDriver) && (
                          <option value={order.deliveryDriver}>
                            {order.deliveryDriver} (no capacity)
                          </option>
                        )}
                    </select>
                  </td>
                  <td>
                    <input
                      type="text"
                      className="table-input col-route"
                      placeholder="Route area"
                      value={order.routeArea}
                      onChange={(e) => update(order.id, { routeArea: e.target.value })}
                    />
                  </td>
                  <td>
                    <select
                      className="table-select col-status"
                      value={order.status}
                      onChange={(e) =>
                        update(order.id, { status: e.target.value as OrderStatus })
                      }
                    >
                      {ORDER_STATUSES.map((s) => (
                        <option key={s} value={s}>
                          {s}
                        </option>
                      ))}
                    </select>
                  </td>
                  <td className="cell-number cell-readonly">{order.finEquivalent.toFixed(1)}</td>
                  <td className="cell-warning cell-readonly">{order.warning ?? ""}</td>
                  <td className="cell-action">
                    <button
                      type="button"
                      className="btn-remove"
                      title="Remove order"
                      aria-label="Remove order"
                      onClick={() => remove(order.id)}
                    >
                      ×
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        </>
      )}
    </section>
  );
}
