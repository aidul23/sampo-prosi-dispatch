import type { RouteSummary as RouteSummaryType } from "../types/dispatch";

interface Props {
  summaries: RouteSummaryType[];
}

export default function RouteSummary({ summaries }: Props) {
  return (
    <section className="card">
      <h2>4. Route summary</h2>
      {summaries.length === 0 ? (
        <p className="status-text">
          No summary yet. Assign delivery drivers and press “Calculate plan”.
        </p>
      ) : (
        <div className="summary-grid">
          {summaries.map((s) => {
            const pct =
              s.capacity > 0
                ? Math.min((s.usedCapacity / s.capacity) * 100, 100)
                : 100;
            return (
              <div
                key={s.driverName}
                className={`summary-card ${s.overloaded ? "summary-overloaded" : ""}`}
              >
                <div className="summary-title">
                  <strong>{s.driverName}</strong>
                  {s.overloaded ? (
                    <span className="badge badge-danger">OVERLOADED</span>
                  ) : (
                    <span className="badge badge-ok">OK</span>
                  )}
                </div>
                <div className="capacity-bar">
                  <div
                    className={`capacity-fill ${s.overloaded ? "fill-danger" : ""}`}
                    style={{ width: `${pct}%` }}
                  />
                </div>
                <dl>
                  <div>
                    <dt>Used / capacity</dt>
                    <dd>
                      {s.usedCapacity.toFixed(1)} / {s.capacity.toFixed(1)} FIN
                    </dd>
                  </div>
                  <div>
                    <dt>Remaining</dt>
                    <dd className={s.remainingCapacity < 0 ? "text-danger" : ""}>
                      {s.remainingCapacity.toFixed(1)} FIN
                    </dd>
                  </div>
                  <div>
                    <dt>Orders</dt>
                    <dd>{s.ordersCount}</dd>
                  </div>
                </dl>
              </div>
            );
          })}
        </div>
      )}
    </section>
  );
}
