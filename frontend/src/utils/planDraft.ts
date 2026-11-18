import type { PlanDraft } from "../types/dispatch";

const DRAFT_KEY = "sampo-dispatch-draft-v1";

export function loadDraft(): PlanDraft | null {
  try {
    const raw = localStorage.getItem(DRAFT_KEY);
    if (!raw) return null;
    return JSON.parse(raw) as PlanDraft;
  } catch {
    return null;
  }
}

export function saveDraft(draft: PlanDraft): void {
  localStorage.setItem(DRAFT_KEY, JSON.stringify(draft));
}

export function clearDraft(): void {
  localStorage.removeItem(DRAFT_KEY);
}

export function formatDraftTime(iso: string): string {
  try {
    return new Date(iso).toLocaleString();
  } catch {
    return iso;
  }
}
