import type { OptimizationChange } from "../types/dispatch";

interface Props {
  title: string;
  changes: OptimizationChange[];
  notes: string[];
  onApply: () => void;
  onApplyAndCalculate: () => void;
  onDismiss: () => void;
  applying: boolean;
}

export default function OptimizationPreview({
  title,
  changes,
  notes,
  onApply,
  onApplyAndCalculate,
  onDismiss,
  applying,
}: Props) {
  return (
    <section className="card optimization-preview">
      <div className="card-header">
        <div>
          <h2>{title}</h2>
          <p className="status-text">
            {changes.length === 0
              ? "No driver assignment changes suggested."
              : `${changes.length} assignment change(s) proposed.`}
          </p>
        </div>
        <div className="optimization-actions">
          <button onClick={onDismiss} disabled={applying}>
            Dismiss
          </button>
          <button onClick={onApply} disabled={applying || changes.length === 0}>
            {applying ? "Applying…" : "Apply optimization"}
          </button>
          <button
            className="btn-primary"
            onClick={onApplyAndCalculate}
            disabled={applying || changes.length === 0}
          >
            {applying ? "Applying…" : "Apply & calculate"}
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
                <th>Consignee</th>
                <th>Route Area</th>
                <th>From</th>
                <th>To</th>
                <th>Reason</th>
              </tr>
            </thead>
            <tbody>
              {changes.map((change) => (
                <tr key={change.orderId}>
                  <td>{change.consignee || "—"}</td>
                  <td>{change.routeArea || "—"}</td>
                  <td>{change.previousDriver || "— unassigned —"}</td>
                  <td>
                    <strong>{change.suggestedDriver}</strong>
                  </td>
                  <td className="muted">{change.reason}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}
