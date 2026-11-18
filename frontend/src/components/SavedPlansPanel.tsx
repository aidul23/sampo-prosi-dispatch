import { useCallback, useEffect, useState } from "react";
import {
  createSavedPlan,
  deleteSavedPlan,
  fetchSavedPlan,
  fetchSavedPlans,
  updateSavedPlan,
} from "../api/client";
import type { DriverCapacity, Order, SavedPlan, SavedPlanSummary } from "../types/dispatch";
import { formatPlanDateFi } from "../utils/date";

interface Props {
  planDate: string;
  orders: Order[];
  drivers: DriverCapacity[];
  activePlanId: string | null;
  planName: string;
  onPlanNameChange: (name: string) => void;
  onPlanLoaded: (plan: SavedPlan) => void;
  onPlanSaved: (plan: SavedPlan) => void;
  onNewPlan: () => void;
  onActivePlanDeleted: () => void;
  onMessage: (message: string) => void;
}

function defaultPlanName(planDate: string): string {
  return `Plan ${formatPlanDateFi(planDate)}`;
}

export default function SavedPlansPanel({
  planDate,
  orders,
  drivers,
  activePlanId,
  planName,
  onPlanNameChange,
  onPlanLoaded,
  onPlanSaved,
  onNewPlan,
  onActivePlanDeleted,
  onMessage,
}: Props) {
  const [plans, setPlans] = useState<SavedPlanSummary[]>([]);
  const [loadingList, setLoadingList] = useState(false);
  const [saving, setSaving] = useState(false);
  const [loadingPlanId, setLoadingPlanId] = useState<string | null>(null);

  const refreshPlans = useCallback(async () => {
    setLoadingList(true);
    try {
      setPlans(await fetchSavedPlans());
    } catch (err) {
      onMessage(`Could not load saved plans: ${(err as Error).message}`);
    } finally {
      setLoadingList(false);
    }
  }, [onMessage]);

  useEffect(() => {
    refreshPlans();
  }, [refreshPlans]);

  async function handleSaveNew() {
    const name = planName.trim() || defaultPlanName(planDate);
    setSaving(true);
    try {
      const saved = await createSavedPlan({ name, planDate, orders, drivers });
      onPlanNameChange(saved.name);
      onPlanSaved(saved);
      await refreshPlans();
      onMessage(`Plan saved as "${saved.name}".`);
    } catch (err) {
      onMessage(`Save failed: ${(err as Error).message}`);
    } finally {
      setSaving(false);
    }
  }

  async function handleUpdate() {
    if (!activePlanId) return;
    const name = planName.trim() || defaultPlanName(planDate);
    setSaving(true);
    try {
      const saved = await updateSavedPlan(activePlanId, {
        name,
        planDate,
        orders,
        drivers,
      });
      onPlanNameChange(saved.name);
      onPlanSaved(saved);
      await refreshPlans();
      onMessage(`Plan "${saved.name}" updated.`);
    } catch (err) {
      onMessage(`Update failed: ${(err as Error).message}`);
    } finally {
      setSaving(false);
    }
  }

  async function handleLoad(planId: string) {
    setLoadingPlanId(planId);
    try {
      const plan = await fetchSavedPlan(planId);
      onPlanLoaded(plan);
      onMessage(`Loaded plan "${plan.name}".`);
    } catch (err) {
      onMessage(`Load failed: ${(err as Error).message}`);
    } finally {
      setLoadingPlanId(null);
    }
  }

  async function handleDelete(plan: SavedPlanSummary) {
    if (
      !window.confirm(
        `Delete saved plan "${plan.name}" (${plan.orderCount} orders)? This cannot be undone.`
      )
    ) {
      return;
    }
    try {
      await deleteSavedPlan(plan.id);
      if (activePlanId === plan.id) {
        onActivePlanDeleted();
      }
      await refreshPlans();
      onMessage(`Deleted plan "${plan.name}".`);
    } catch (err) {
      onMessage(`Delete failed: ${(err as Error).message}`);
    }
  }

  return (
    <section className="card saved-plans-card">
      <div className="card-header">
        <div>
          <h2>Saved plans</h2>
          <p className="status-text">
            Save to server, load later, update or delete. A local browser draft is kept automatically.
          </p>
        </div>
        <button type="button" onClick={onNewPlan}>
          New plan
        </button>
      </div>

      <div className="saved-plans-form">
        <label className="plan-date-field">
          <span className="plan-date-label">Plan name</span>
          <input
            type="text"
            value={planName}
            placeholder={defaultPlanName(planDate)}
            onChange={(e) => onPlanNameChange(e.target.value)}
          />
        </label>
        <div className="saved-plans-actions">
          <button type="button" onClick={handleSaveNew} disabled={saving || orders.length === 0}>
            {saving ? "Saving…" : "Save as new"}
          </button>
          <button
            type="button"
            className="btn-primary"
            onClick={handleUpdate}
            disabled={saving || !activePlanId || orders.length === 0}
          >
            {saving ? "Updating…" : "Update saved plan"}
          </button>
        </div>
      </div>

      {activePlanId && (
        <p className="status-text saved-plans-active">
          Editing saved plan <strong>{planName || activePlanId}</strong> (id: {activePlanId})
        </p>
      )}

      <div className="table-wrap">
        <table className="saved-plans-table">
          <thead>
            <tr>
              <th>Name</th>
              <th>Plan date</th>
              <th className="col-num">Orders</th>
              <th>Last updated</th>
              <th className="col-action">Actions</th>
            </tr>
          </thead>
          <tbody>
            {loadingList && plans.length === 0 ? (
              <tr>
                <td colSpan={5} className="status-text">
                  Loading saved plans…
                </td>
              </tr>
            ) : plans.length === 0 ? (
              <tr>
                <td colSpan={5} className="status-text">
                  No saved plans yet.
                </td>
              </tr>
            ) : (
              plans.map((plan) => (
                <tr key={plan.id} className={plan.id === activePlanId ? "row-active-plan" : ""}>
                  <td>{plan.name}</td>
                  <td>{formatPlanDateFi(plan.planDate)}</td>
                  <td className="cell-number">{plan.orderCount}</td>
                  <td>{new Date(plan.updatedAt).toLocaleString()}</td>
                  <td className="cell-action saved-plans-row-actions">
                    <button
                      type="button"
                      onClick={() => handleLoad(plan.id)}
                      disabled={loadingPlanId === plan.id}
                    >
                      {loadingPlanId === plan.id ? "Loading…" : "Load"}
                    </button>
                    <button type="button" className="btn-danger-text" onClick={() => handleDelete(plan)}>
                      Delete
                    </button>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </section>
  );
}
