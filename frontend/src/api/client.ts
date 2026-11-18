import type {
  AddressBookEntry,
  DriverCapacity,
  GeocodeResponse,
  OptimizeMode,
  OptimizeResponse,
  Order,
  PlanResponse,
  SavePlanPayload,
  SavedPlan,
  SavedPlanSummary,
  StopOptimizeResponse,
} from "../types/dispatch";

function normalizeApiBaseUrl(url: string): string {
  const trimmed = url.replace(/\/$/, "");
  if (trimmed === "/api" || trimmed.endsWith("/api")) return trimmed;
  if (trimmed.startsWith("http")) return `${trimmed}/api`;
  return trimmed;
}

const BASE_URL = normalizeApiBaseUrl(import.meta.env.VITE_API_URL ?? "/api");

async function handleJson<T>(response: Response): Promise<T> {
  if (!response.ok) {
    let detail = `Request failed (${response.status})`;
    try {
      const body = await response.json();
      if (body?.detail) detail = String(body.detail);
    } catch {
      // keep default message
    }
    throw new Error(detail);
  }
  return response.json() as Promise<T>;
}

export async function uploadExcel(file: File): Promise<Order[]> {
  const formData = new FormData();
  formData.append("file", file);
  const response = await fetch(`${BASE_URL}/upload-excel`, {
    method: "POST",
    body: formData,
  });
  return handleJson<Order[]>(response);
}

export async function fetchSampleOrders(): Promise<Order[]> {
  const response = await fetch(`${BASE_URL}/sample-orders`);
  return handleJson<Order[]>(response);
}

export async function calculatePlan(
  orders: Order[],
  drivers: DriverCapacity[]
): Promise<PlanResponse> {
  const response = await fetch(`${BASE_URL}/calculate-plan`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ orders, drivers }),
  });
  return handleJson<PlanResponse>(response);
}

export async function optimizeRoutes(
  orders: Order[],
  drivers: DriverCapacity[],
  mode: OptimizeMode = "unassigned_only"
): Promise<OptimizeResponse> {
  const response = await fetch(`${BASE_URL}/optimize-routes`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ orders, drivers, mode }),
  });
  return handleJson<OptimizeResponse>(response);
}

export async function optimizeStopOrder(
  orders: Order[],
  drivers: DriverCapacity[]
): Promise<StopOptimizeResponse> {
  const response = await fetch(`${BASE_URL}/optimize-stop-order`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ orders, drivers }),
  });
  return handleJson<StopOptimizeResponse>(response);
}

export async function geocodeOrders(orders: Order[]): Promise<GeocodeResponse> {
  const response = await fetch(`${BASE_URL}/geocode-orders`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ orders }),
  });
  return handleJson<GeocodeResponse>(response);
}

export async function fetchAddressBook(): Promise<AddressBookEntry[]> {
  const response = await fetch(`${BASE_URL}/address-book`);
  return handleJson<AddressBookEntry[]>(response);
}

export async function saveAddressBookEntry(
  consignee: string,
  address: string,
  entryId?: string
): Promise<AddressBookEntry> {
  const response = await fetch(
    entryId ? `${BASE_URL}/address-book/${entryId}` : `${BASE_URL}/address-book`,
    {
      method: entryId ? "PUT" : "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ consignee, address }),
    }
  );
  return handleJson<AddressBookEntry>(response);
}

export async function saveAddressBookEntries(
  entries: { consignee: string; address: string }[]
): Promise<AddressBookEntry[]> {
  const response = await fetch(`${BASE_URL}/address-book/bulk`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ entries }),
  });
  return handleJson<AddressBookEntry[]>(response);
}

export async function deleteAddressBookEntry(entryId: string): Promise<void> {
  const response = await fetch(`${BASE_URL}/address-book/${entryId}`, { method: "DELETE" });
  await handleJson<unknown>(response);
}

export async function applyAddressBook(orders: Order[]): Promise<Order[]> {
  const response = await fetch(`${BASE_URL}/address-book/apply`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ orders }),
  });
  return handleJson<Order[]>(response);
}

export async function fetchSavedPlans(): Promise<SavedPlanSummary[]> {
  const response = await fetch(`${BASE_URL}/plans`);
  return handleJson<SavedPlanSummary[]>(response);
}

export async function fetchSavedPlan(planId: string): Promise<SavedPlan> {
  const response = await fetch(`${BASE_URL}/plans/${planId}`);
  return handleJson<SavedPlan>(response);
}

export async function createSavedPlan(payload: SavePlanPayload): Promise<SavedPlan> {
  const response = await fetch(`${BASE_URL}/plans`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  return handleJson<SavedPlan>(response);
}

export async function updateSavedPlan(
  planId: string,
  payload: SavePlanPayload
): Promise<SavedPlan> {
  const response = await fetch(`${BASE_URL}/plans/${planId}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  return handleJson<SavedPlan>(response);
}

export async function deleteSavedPlan(planId: string): Promise<void> {
  const response = await fetch(`${BASE_URL}/plans/${planId}`, { method: "DELETE" });
  if (!response.ok) {
    let detail = `Delete failed (${response.status})`;
    try {
      const body = await response.json();
      if (body?.detail) detail = String(body.detail);
    } catch {
      // keep default message
    }
    throw new Error(detail);
  }
}

export async function exportDriverSheets(
  orders: Order[],
  drivers: DriverCapacity[],
  planDate?: string
): Promise<void> {
  const response = await fetch(`${BASE_URL}/export-driver-sheets`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ orders, drivers, planDate }),
  });
  if (!response.ok) {
    let detail = `Export failed (${response.status})`;
    try {
      const body = await response.json();
      if (body?.detail) detail = String(body.detail);
    } catch {
      // keep default message
    }
    throw new Error(detail);
  }
  const blob = await response.blob();
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  const fallbackDate = new Date().toISOString().slice(0, 10);
  link.download = `dispatch-plan-${planDate || fallbackDate}.xlsx`;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}
