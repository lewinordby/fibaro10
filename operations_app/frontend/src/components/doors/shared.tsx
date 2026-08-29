export type RecordValue = Record<string, any>;

export type DoorStatus = {
  generatedAt: string;
  summary: RecordValue;
  doors: RecordValue[];
  changes: RecordValue[];
  events: RecordValue[];
  periods: RecordValue[];
};

export type Sunrooms = {
  generatedAt: string;
  ntfyDoorsSubscribeUrl?: string;
  ntfyDoorsWebUrl?: string;
  rules: RecordValue;
  summary: RecordValue;
  rooms: RecordValue[];
};

export type RoomOverview = {
  generatedAt: string;
  dayDate?: string;
  dayStart?: string;
  dayEnd?: string;
  summary: RecordValue;
  rules: RecordValue;
  rooms: RecordValue[];
};

export type DoorAlarms = Sunrooms & {
  alarms: RecordValue[];
  watch: RecordValue[];
  occupiedWithoutSession: RecordValue[];
  history: RecordValue[];
};

export type SunroomLogic = {
  generatedAt: string;
  windowHours: number;
  summary: RecordValue;
  rules: RecordValue;
  scraper: RecordValue;
  rooms: RecordValue[];
  events: RecordValue[];
};

export function localDay() {
  return new Date().toLocaleDateString("sv-SE", { timeZone: "Europe/Oslo" });
}

export function shiftDay(day: string, amount: number) {
  const value = new Date(`${day}T12:00:00`);
  value.setDate(value.getDate() + amount);
  return value.toLocaleDateString("sv-SE");
}

export function stamp(value?: string | null) {
  return value
    ? new Date(value).toLocaleString("nb-NO", {
        day: "2-digit",
        month: "2-digit",
        hour: "2-digit",
        minute: "2-digit",
        second: "2-digit",
        timeZone: "Europe/Oslo",
      })
    : "-";
}

export function timeStamp(value?: string | null) {
  return value
    ? new Date(value).toLocaleTimeString("nb-NO", {
        hour: "2-digit",
        minute: "2-digit",
        second: "2-digit",
        timeZone: "Europe/Oslo",
      })
    : "-";
}

export function tone(value?: string) {
  return String(value) === "unknown"
    ? "gray"
    : ["alert", "alarm"].includes(String(value))
      ? "red"
      : ["warning", "waiting"].includes(String(value))
        ? "yellow"
        : ["active", "closed"].includes(String(value))
          ? "sky"
          : "green";
}

export function badge(value: string, color: string) {
  const classes: Record<string, string> = {
    red: "bg-red-500/10 text-red-700 dark:text-red-300",
    yellow: "bg-yellow-500/10 text-yellow-700 dark:text-yellow-300",
    sky: "bg-sky-500/10 text-sky-700 dark:text-sky-300",
    green: "bg-green-500/10 text-green-700 dark:text-green-300",
    gray: "bg-gray-500/10 text-gray-600 dark:text-gray-300",
  };
  return <span className={`rounded-full px-2.5 py-1 text-xs font-semibold ${classes[color]}`}>{value}</span>;
}

export function SummaryStrip({ items }: { items: { label: string; value: string | number; detail?: string; color?: string }[] }) {
  const colorClasses: Record<string, string> = {
    green: "border-l-green-500",
    red: "border-l-red-500",
    yellow: "border-l-yellow-500",
    sky: "border-l-sky-500",
    gray: "border-l-gray-400",
  };
  return (
    <div className="grid overflow-hidden rounded-xl border border-gray-200 bg-white shadow-sm sm:grid-cols-2 xl:grid-cols-4 dark:border-gray-700 dark:bg-gray-800">
      {items.map((item) => (
        <div className={`border-b border-l-4 border-gray-100 px-4 py-3 last:border-b-0 sm:border-b-0 sm:border-r dark:border-gray-700 ${colorClasses[item.color || "gray"]}`} key={item.label}>
          <span className="block text-xs font-semibold text-gray-500 dark:text-gray-400">{item.label}</span>
          <strong className="mt-0.5 block text-xl font-bold tabular-nums text-gray-900 dark:text-gray-100">{item.value}</strong>
          {item.detail ? <span className="mt-0.5 block text-xs text-gray-500 dark:text-gray-400">{item.detail}</span> : null}
        </div>
      ))}
    </div>
  );
}

const FIRST_FLOOR_DOORS = new Set([
  "door_solrom_01",
  "door_solrom_02",
  "door_solrom_03",
  "door_solrom_09",
  "door_413",
  "door_inngang",
  "door_toalett",
]);

const VIP_DOORS = new Set([
  "door_solrom_10",
  "door_solrom_11",
  "door_solrom_12",
  "door_453",
  "door_massasjestudio",
  "door_loftluke_massasje",
]);

export function doorDepartment(door: RecordValue) {
  const deviceKey = String(door.deviceKey || "");
  if (FIRST_FLOOR_DOORS.has(deviceKey)) return "1etg";
  if (VIP_DOORS.has(deviceKey)) return "vip";
  return "2etg";
}

export function departmentDoorOrder(door: RecordValue) {
  return door.groupKey === "solrom"
    ? Number(door.sortOrder || 0)
    : 1000 + Number(door.sortOrder || 0);
}
