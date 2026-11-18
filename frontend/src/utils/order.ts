import type { Order } from "../types/dispatch";

/** Fill fields added in later versions (old saved plans / browser drafts). */
export function withOrderDefaults(order: Order): Order {
  return {
    ...order,
    address: order.address ?? "",
    lat: order.lat ?? null,
    lng: order.lng ?? null,
    geocodePrecision: order.geocodePrecision ?? null,
  };
}

export function hasExactLocation(order: Order): boolean {
  return order.lat != null && order.lng != null && !!order.geocodePrecision;
}

/** Copy only the location fields from a geocoded order onto the current one. */
export function mergeLocation(current: Order, located: Order): Order {
  if (current.address !== located.address && current.address.trim() !== "") {
    // Address was edited while geocoding ran — keep the edit, drop stale coords.
    return current;
  }
  return {
    ...current,
    address: located.address,
    lat: located.lat ?? null,
    lng: located.lng ?? null,
    geocodePrecision: located.geocodePrecision ?? null,
  };
}

export const PRECISION_LABEL: Record<string, string> = {
  address: "Exact address",
  postal_code: "Postal code area",
  area: "Approximate (route area centre)",
};
