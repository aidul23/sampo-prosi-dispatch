import { addDays, formatPlanDateEn, formatPlanDateFi, todayIso } from "../utils/date";

interface Props {
  planDate: string;
  onChange: (date: string) => void;
}

export default function PlanDatePicker({ planDate, onChange }: Props) {
  return (
    <section className="card plan-date-card">
      <h2>Plan date</h2>
      <div className="plan-date-row">
        <label className="plan-date-field">
          <span className="plan-date-label">Select day</span>
          <input
            type="date"
            className="plan-date-input"
            value={planDate}
            onChange={(e) => onChange(e.target.value)}
          />
        </label>
        <div className="plan-date-summary">
          <strong>{formatPlanDateFi(planDate)}</strong>
          <span className="muted">{formatPlanDateEn(planDate)}</span>
        </div>
        <div className="plan-date-actions">
          <button type="button" onClick={() => onChange(todayIso())}>
            Today
          </button>
          <button type="button" onClick={() => onChange(addDays(planDate, 1))}>
            +1 day
          </button>
        </div>
      </div>
      <p className="status-text">
        Each daily plan is tied to this date. &ldquo;Create next day plan&rdquo; advances the date
        and rolls over unfinished orders.
      </p>
    </section>
  );
}
