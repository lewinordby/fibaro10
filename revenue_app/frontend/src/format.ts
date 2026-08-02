export function nok(value: number, digits = 0) {
  return new Intl.NumberFormat("nb-NO", {
    minimumFractionDigits: digits,
    maximumFractionDigits: digits,
  }).format(Number.isFinite(value) ? value : 0);
}

export function signedNok(value: number) {
  if (!Number.isFinite(value) || value === 0) return "0 kr";
  return `${value > 0 ? "+" : "-"}${nok(Math.abs(value))} kr`;
}

export function percentDelta(current: number, previous: number) {
  if (!Number.isFinite(current) || !Number.isFinite(previous) || previous === 0) return "-";
  const value = ((current - previous) / previous) * 100;
  return `${value > 0 ? "+" : ""}${value.toFixed(0)}%`;
}

export function shortDateTime(value?: string | null) {
  if (!value) return "-";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "-";
  return date.toLocaleString("nb-NO", { day: "2-digit", month: "2-digit", hour: "2-digit", minute: "2-digit" });
}

export function valueLabel(key: string) {
  const labels: Record<string, string> = {
    period_label: "Periode",
    total_paid: "Sum",
    total_count: "Antall totalt",
    parking_paid: "Parkering",
    parking_count: "Parkeringer",
    sun_paid: "Soling",
    sun_count: "Solinger",
    week_label: "Uke",
    date_range: "Datoer",
  };
  return labels[key] || key.replaceAll("_", " ").replace(/^./, (letter) => letter.toUpperCase());
}

export function displayCell(key: string, value: unknown) {
  if (value == null || value === "") return "-";
  if (typeof value === "number") {
    if (key.includes("paid") || key.includes("amount") || key.includes("revenue") || key === "total") return `${nok(value)} kr`;
    return nok(value, Number.isInteger(value) ? 0 : 1);
  }
  return String(value);
}

