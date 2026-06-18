import type { PalletType } from "../types/dispatch";

// FIN pallet (1200x1000) is the base unit. EUR (1200x800) counts as 0.8 FIN.
const PALLET_FACTORS: Record<PalletType, number> = {
  FIN: 1.0,
  EUR: 0.8,
  OTHER: 1.0,
};

export function finEquivalent(
  pallets: number,
  palletType: PalletType,
  stackable: boolean
): number {
  let load = pallets * (PALLET_FACTORS[palletType] ?? 1.0);
  if (stackable) load /= 2;
  return Math.round(load * 100) / 100;
}
