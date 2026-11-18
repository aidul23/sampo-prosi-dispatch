import { useMemo } from "react";
import {
  CircleMarker,
  MapContainer,
  Polyline,
  Popup,
  TileLayer,
  Tooltip,
} from "react-leaflet";
import type { Order } from "../types/dispatch";
import {
  DEPOT,
  DEPOT_ADDRESS,
  DEPOT_NAME,
  driverColor,
  getCentroid,
  jitterCoords,
} from "../data/areaCentroids";
import type { LatLng } from "../data/areaCentroids";
import { hasExactLocation, PRECISION_LABEL } from "../utils/order";
import "leaflet/dist/leaflet.css";

interface Props {
  orders: Order[];
}

/** Exact geocoded position when available, else jittered route area centre. */
function orderPosition(order: Order): LatLng {
  if (hasExactLocation(order)) return { lat: order.lat!, lng: order.lng! };
  return jitterCoords(getCentroid(order.routeArea), order.id);
}

function sortForRoute(driverOrders: Order[]): Order[] {
  return [...driverOrders].sort((a, b) => {
    const seqA = a.stopSequence ?? 9999;
    const seqB = b.stopSequence ?? 9999;
    if (seqA !== seqB) return seqA - seqB;
    return a.consignee.localeCompare(b.consignee);
  });
}

export default function RouteMap({ orders }: Props) {
  const drivers = useMemo(
    () =>
      Array.from(
        new Set(orders.map((o) => o.deliveryDriver.trim()).filter(Boolean))
      ).sort(),
    [orders]
  );

  const routes = useMemo(() => {
    const grouped = new Map<string, Order[]>();
    for (const order of orders) {
      const driver = order.deliveryDriver.trim();
      if (!driver) continue;
      const list = grouped.get(driver) ?? [];
      list.push(order);
      grouped.set(driver, list);
    }
    return Array.from(grouped.entries()).map(([driver, driverOrders]) => {
      const sorted = sortForRoute(driverOrders);
      const line: [number, number][] = [
        [DEPOT.lat, DEPOT.lng],
        ...sorted.map((order) => {
          const point = orderPosition(order);
          return [point.lat, point.lng] as [number, number];
        }),
      ];
      return { driver, orders: sorted, line, color: driverColor(driver, drivers) };
    });
  }, [orders, drivers]);

  const exactCount = orders.filter(hasExactLocation).length;

  if (orders.length === 0) {
    return (
      <section className="card route-map-card">
        <h2>Route map</h2>
        <p className="status-text">Load orders to see delivery areas on the map.</p>
      </section>
    );
  }

  return (
    <section className="card route-map-card">
      <div className="card-header">
        <div>
          <h2>Route map</h2>
          <p className="status-text">
            OpenStreetMap view. Depot: {DEPOT_ADDRESS}. Pins colored by delivery
            driver; {exactCount}/{orders.length} at their address or postal code, the
            rest (dashed outline) at the route area centre. Lines are straight
            connections in stop order, not the driven road.
          </p>
        </div>
        <div className="map-legend">
          <span className="map-legend-item">
            <span className="map-legend-swatch depot" /> {DEPOT_NAME} depot
          </span>
          {drivers.map((driver) => (
            <span key={driver} className="map-legend-item">
              <span
                className="map-legend-swatch"
                style={{ background: driverColor(driver, drivers) }}
              />
              {driver}
            </span>
          ))}
          <span className="map-legend-item">
            <span className="map-legend-swatch unassigned" /> Unassigned
          </span>
        </div>
      </div>

      <div className="route-map-wrap">
        <MapContainer
          center={[DEPOT.lat, DEPOT.lng]}
          zoom={6}
          scrollWheelZoom
          className="route-map"
        >
          <TileLayer
            attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
            url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
          />

          <CircleMarker
            center={[DEPOT.lat, DEPOT.lng]}
            radius={9}
            pathOptions={{
              color: "#111",
              fillColor: "#111",
              fillOpacity: 1,
              weight: 2,
            }}
          >
            <Tooltip permanent direction="top" offset={[0, -8]}>
              Depot: {DEPOT_ADDRESS}
            </Tooltip>
          </CircleMarker>

          {routes.map(({ driver, line, color }) => (
            <Polyline
              key={`line-${driver}`}
              positions={line}
              pathOptions={{ color, weight: 3, opacity: 0.75, dashArray: "6 4" }}
            />
          ))}

          {orders.map((order) => {
            const driver = order.deliveryDriver.trim();
            const point = orderPosition(order);
            const exact = hasExactLocation(order);
            const color = driver ? driverColor(driver, drivers) : "#999999";
            return (
              <CircleMarker
                key={order.id}
                center={[point.lat, point.lng]}
                radius={exact ? 7 : 6}
                pathOptions={{
                  color: exact ? "#fff" : "#555",
                  dashArray: exact ? undefined : "2 2",
                  weight: 1.5,
                  fillColor: color,
                  fillOpacity: 0.9,
                }}
              >
                <Popup>
                  <strong>{order.consignee || "—"}</strong>
                  <br />
                  {order.address && (
                    <>
                      {order.address}
                      <br />
                    </>
                  )}
                  Location: {PRECISION_LABEL[order.geocodePrecision ?? "area"]}
                  <br />
                  Area: {order.routeArea || "Unspecified"}
                  <br />
                  Driver: {driver || "Unassigned"}
                  {order.stopSequence != null && (
                    <>
                      <br />
                      Stop #: {order.stopSequence}
                    </>
                  )}
                </Popup>
              </CircleMarker>
            );
          })}
        </MapContainer>
      </div>
    </section>
  );
}
