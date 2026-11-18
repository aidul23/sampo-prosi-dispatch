import type { StopOptimizationChange } from "../types/dispatch";

interface Props {
  changes: StopOptimizationChange[];
  notes: string[];
  onApply: () => void;
  onDismiss: () => void;
  applying: boolean;
}

export default function StopOptimizationPreview({
  changes,
  notes,
  onApply,
  onDismiss,
  applying,
}: Props) {
  return (
    <section className="card optimization-preview">
      <div className="card-header">
        <div>
          <h2>Stop order preview</h2>
          <p className="status-text">
            {changes.length === 0
              ? "Stop order is already optimal or no assigned routes."
              : `${changes.length} stop sequence change(s) proposed.`}
          </p>
        </div>
        <div className="optimization-actions">
          <button onClick={onDismiss} disabled={applying}>
            Dismiss
          </button>
          <button
            className="btn-primary"
            onClick={onApply}
            disabled={applying || changes.length === 0}
          >
            {applying ? "Applying…" : "Apply stop order"}
          </button>
        </div>
      </div>

      {notes.length > 0 && (
        <ul className="optimization-notes">
          {notes.map((note) => (
            <li key={note}>{note}</li>
          ))}
        </ul>
      )}

      {changes.length > 0 && (
        <div className="table-wrap">
          <table className="optimization-table">
            <thead>
              <tr>
                <th>Driver</th>
                <th>Consignee</th>
                <th>Route Area</th>
                <th className="col-num">From #</th>
                <th className="col-num">To #</th>
              </tr>
            </thead>
            <tbody>
              {changes.map((change) => (
                <tr key={`${change.orderId}-${change.suggestedSequence}`}>
                  <td>{change.deliveryDriver}</td>
                  <td>{change.consignee || "—"}</td>
                  <td>{change.routeArea || "—"}</td>
                  <td className="cell-number">
                    {change.previousSequence ?? "—"}
                  </td>
                  <td className="cell-number">
                    <strong>{change.suggestedSequence}</strong>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}
