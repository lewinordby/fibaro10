export type TableSort = { column: string; direction: "asc" | "desc" } | null;

function displayValue(value: unknown) {
  if (value === null || value === undefined) return "";
  if (Array.isArray(value)) return value.join(" ");
  if (typeof value === "object") return Object.values(value as Record<string, unknown>).join(" ");
  return String(value);
}

function compact(value: string) {
  return value.toLocaleLowerCase("nb-NO").replace(/[^a-z0-9\u00e6\u00f8\u00e5]/gi, "");
}

export function filterTableRows<T extends Record<string, unknown>>(rows: T[], columns: string[], query: string): T[] {
  const normalized = query.trim().toLocaleLowerCase("nb-NO");
  if (!normalized) return rows;
  const quoted = normalized.length >= 2 && normalized[0] === normalized.at(-1) && ["\"", "'"].includes(normalized[0]);
  const exact = quoted ? normalized.slice(1, -1).trim() : "";
  const exactPattern = exact
    ? new RegExp(`(^|[^\\p{L}\\p{N}_])${exact.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")}($|[^\\p{L}\\p{N}_])`, "iu")
    : null;
  const compactQuery = compact(exact || normalized);
  return rows.filter((row) => columns.some((column) => {
    const value = displayValue(row[column]).toLocaleLowerCase("nb-NO");
    if (exactPattern) return exactPattern.test(value) || (compactQuery.length > 1 && compact(value) === compactQuery);
    return value.includes(normalized) || (compactQuery.length > 1 && compact(value).includes(compactQuery));
  }));
}

function sortable(value: unknown): number | string {
  if (value === null || value === undefined || value === "") return "";
  if (typeof value === "boolean") return value ? 1 : 0;
  if (typeof value === "number") return Number.isFinite(value) ? value : "";
  const text = String(value).trim();
  if (/^\d{4}-\d{2}-\d{2}/.test(text)) {
    const timestamp = new Date(text).getTime();
    if (!Number.isNaN(timestamp)) return timestamp;
  }
  const numeric = Number(text.replaceAll(" ", "").replace(",", "."));
  return Number.isFinite(numeric) && /^[-+]?\d[\d\s]*(?:[.,]\d+)?$/.test(text) ? numeric : text.toLocaleLowerCase("nb-NO");
}

export function sortTableRows<T extends Record<string, unknown>>(rows: T[], sort: TableSort): T[] {
  if (!sort) return rows;
  const direction = sort.direction === "asc" ? 1 : -1;
  return rows.map((row, index) => ({ row, index })).sort((left, right) => {
    const a = sortable(left.row[sort.column]);
    const b = sortable(right.row[sort.column]);
    if (a === b) return left.index - right.index;
    if (a === "") return 1;
    if (b === "") return -1;
    if (typeof a === "number" && typeof b === "number") return (a - b) * direction;
    return String(a).localeCompare(String(b), "nb-NO", { numeric: true, sensitivity: "base" }) * direction;
  }).map(({ row }) => row);
}
