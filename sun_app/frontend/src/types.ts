import type { JsonRecord } from "@lilletorget/microapp-ui/types";

export type SunTimelineItem = {
  left: number;
  width: number;
  label: string;
  title: string;
  kind: "standard" | "member" | "no-member";
  href: string;
};
export type SunTimelineRoom = {
  roomId: string;
  label: string;
  sessions: SunTimelineItem[];
  count: number;
  minutes: number;
  paid: number;
};

export type SunTimeline = {
  selectedDay: string;
  selectedDayLabel: string;
  prevDay: string;
  nextDay: string;
  rooms: SunTimelineRoom[];
  aggregateSessions: SunTimelineItem[];
  totals: { sessionsCount: number; durationMinutes: number; durationHours: number; paidAmountKr: number };
  ticks: Array<{ label: string; left: number }>;
  nowMarker: number | null;
};

export type SunSessionSavedImage = {
  id: number;
  snapshotId: string;
  capturedAt: string | null;
  label: string;
  imageUrl: string;
  offsetSeconds: number;
  offsetLabel: string;
  deltaSeconds?: number | null;
  isPrimary?: boolean;
  source?: string;
};

export type SunSessionSnapshot = {
  id: string;
  capturedAt: string;
  label: string;
  filename: string;
  imageUrl: string;
  deltaSeconds: number | null;
  isLinked: boolean;
};

export type SunSessionImageBrowser = {
  sessionId: number;
  startedAt: string | null;
  targetAt: string | null;
  targetLabel: string;
  seriesOffsets: number[];
  snapshotRoot: string;
  archiveDay: string;
  snapshotsFound: number;
  linked: SunSessionSavedImage | null;
  savedImages: SunSessionSavedImage[];
  current: SunSessionSnapshot | null;
  previousSnapshotId: string | null;
  nextSnapshotId: string | null;
  canPrevious: boolean;
  canNext: boolean;
};
