export type PalletType = "FIN" | "EUR" | "OTHER";

export type OrderStatus = "NEW" | "PLANNED" | "DELIVERED" | "CARRY_OVER";

export interface Order {
  id: string;
  customer: string;
  pickupDriver: string;
  consignee: string;
  pallets: number;
  palletType: PalletType;
  stackable: boolean;
  extraInfo: string;
  deliveryDriver: string;
  routeArea: string;
  status: OrderStatus;
  finEquivalent: number;
  warning: string | null;
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

export const PALLET_TYPES: PalletType[] = ["FIN", "EUR", "OTHER"];

export const ORDER_STATUSES: OrderStatus[] = [
  "NEW",
  "PLANNED",
  "DELIVERED",
  "CARRY_OVER",
];
