export type PalletType = "FIN" | "EUR" | "OTHER";

export type OrderStatus = "NEW" | "PLANNED" | "DELIVERED" | "CARRY_OVER";

/**
 * address = street address found; postal_code = postal code area only;
 * not_found = looked up, nothing found. null = no address / not looked up yet.
 */
export type GeocodePrecision = "address" | "postal_code" | "not_found";

export interface Order {
  id: string;
  customer: string;
  pickupDriver: string;
  consignee: string;
  address: string;
  lat?: number | null;
  lng?: number | null;
  geocodePrecision?: GeocodePrecision | null;
  pallets: number;
  palletType: PalletType;
  stackable: boolean;
  extraInfo: string;
  deliveryDriver: string;
  routeArea: string;
  status: OrderStatus;
  finEquivalent: number;
  warning: string | null;
  stopSequence?: number | null;
}

export interface DriverCapacity {
  driverName: string;
  truckCapacity: number;
}

export interface RouteSummary {
  driverName: string;
  capacity: number;
  usedCapacity: number;
  remainingCapacity: number;
  overloaded: boolean;
  ordersCount: number;
}

export interface PlanResponse {
  orders: Order[];
  routeSummaries: RouteSummary[];
}

export type OptimizeMode = "unassigned_only" | "all";

export interface OptimizationChange {
  orderId: string;
  consignee: string;
  routeArea: string;
  previousDriver: string;
  suggestedDriver: string;
  reason: string;
}

export interface OptimizeResponse {
  orders: Order[];
  changes: OptimizationChange[];
  routeSummaries: RouteSummary[];
  notes: string[];
}

export interface StopOptimizationChange {
  orderId: string;
  consignee: string;
  deliveryDriver: string;
  routeArea: string;
  previousSequence: number | null;
  suggestedSequence: number;
  reason: string;
}

export interface StopOptimizeResponse {
  orders: Order[];
  changes: StopOptimizationChange[];
  routeSummaries: RouteSummary[];
  notes: string[];
}

export interface SavedPlanSummary {
  id: string;
  name: string;
  planDate: string;
  orderCount: number;
  updatedAt: string;
}

export interface SavedPlan {
  id: string;
  name: string;
  planDate: string;
  orders: Order[];
  drivers: DriverCapacity[];
  createdAt: string;
  updatedAt: string;
}

export interface SavePlanPayload {
  name: string;
  planDate: string;
  orders: Order[];
  drivers: DriverCapacity[];
}

export interface PlanDraft {
  planDate: string;
  orders: Order[];
  drivers: DriverCapacity[];
  activePlanId: string | null;
  activePlanName: string;
  savedAt: string;
}

export interface GeocodeResponse {
  orders: Order[];
  located: number;
  pending: number;
  failed: number;
  notes: string[];
}

export interface AddressBookEntry {
  id: string;
  consignee: string;
  address: string;
  updatedAt: string;
}

export const PALLET_TYPES: PalletType[] = ["FIN", "EUR", "OTHER"];

export const ORDER_STATUSES: OrderStatus[] = [
  "NEW",
  "PLANNED",
  "DELIVERED",
  "CARRY_OVER",
];
