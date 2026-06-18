import type { DriverCapacity, Order, PlanResponse } from "../types/dispatch";

const BASE_URL = import.meta.env.VITE_API_URL ?? "/api";

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
