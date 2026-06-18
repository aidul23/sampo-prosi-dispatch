const FI_DAYS = [
  "Sunnuntai",
  "Maanantai",
  "Tiistai",
  "Keskiviikko",
  "Torstai",
  "Perjantai",
  "Lauantai",
];

const EN_DAYS = [
  "Sunday",
  "Monday",
  "Tuesday",
  "Wednesday",
  "Thursday",
  "Friday",
  "Saturday",
];

export function todayIso(): string {
  const now = new Date();
  const year = now.getFullYear();
  const month = String(now.getMonth() + 1).padStart(2, "0");
  const day = String(now.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
}

export function parseIsoDate(isoDate: string): Date {
  const [year, month, day] = isoDate.split("-").map(Number);
  return new Date(year, month - 1, day);
}

export function addDays(isoDate: string, days: number): string {
  const date = parseIsoDate(isoDate);
  date.setDate(date.getDate() + days);
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, "0");
  const day = String(date.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
}

/** Matches the customer's Excel title format, e.g. "Tiistai 28.4.2026". */
export function formatPlanDateFi(isoDate: string): string {
  const date = parseIsoDate(isoDate);
  const dayName = FI_DAYS[date.getDay()];
  return `${dayName} ${date.getDate()}.${date.getMonth() + 1}.${date.getFullYear()}`;
}

export function formatPlanDateEn(isoDate: string): string {
  const date = parseIsoDate(isoDate);
  const dayName = EN_DAYS[date.getDay()];
  return `${dayName}, ${isoDate}`;
}

export function formatExportFilename(isoDate: string): string {
  return `dispatch-plan-${isoDate}.xlsx`;
}
