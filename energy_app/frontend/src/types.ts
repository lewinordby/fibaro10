import type { JsonRecord } from "@lilletorget/microapp-ui/types";

export type EnergyElviaSummaryItem = {
  period?: string | null;
  period_label?: string | null;
  consumption_kwh: number;
  production_kwh: number;
  hours_count: number;
  estimated_hours_count: number;
  days_count: number;
};
export type EnergyElviaData = {
  summary: { total: EnergyElviaSummaryItem; firstAt?: string | null; lastAt?: string | null };
  yearly: EnergyElviaSummaryItem[];
  topDays: EnergyElviaSummaryItem[];
  topMonths: EnergyElviaSummaryItem[];
  imports: JsonRecord[];
  rows: JsonRecord[];
  latestImport?: JsonRecord | null;
  status?: JsonRecord | null;
  uploadEndpoint: string;
};
export type EnergySunbedRoom = { room_id?: string | null; label: string; sun2_bed_id?: string | null; bed_model?: string | null; samples_count: number; sessions_count: number; avg_w?: number | null; estimate_w?: number | null; p25_w?: number | null; p75_w?: number | null; kwh_15_min?: number | null; estimated_kwh?: number | null; confidence: string };
export type EnergySunbedObservation = { session_id: number; label: string; start: string | null; duration_minutes?: number | null; samples_count: number; avg_w?: number | null; avg_observed_w?: number | null; avg_baseline_w?: number | null; estimated_kwh?: number | null };
export type EnergySunbedsData = { dateFrom: string; dateTo: string; maxDays: number; maxPower: number; rooms: EnergySunbedRoom[]; observations: EnergySunbedObservation[]; summary: JsonRecord };
export type EnergyLoadItem = { id: number; name: string; loadType?: string | null; area?: string | null; powerProfile?: "unknown" | "fixed" | "variable" | string | null; expectedPowerW?: number | null; minPowerW?: number | null; maxPowerW?: number | null; measuredDirect?: boolean | null; energyNodeId?: number | null; fibaroDeviceId?: number | null; fibaroMeterId?: number | null; zwaveSwitchId?: number | null; controllable?: boolean | null; active?: boolean | null; critical?: boolean | null; note?: string | null };
export type EnergyAggregateMeter = { key: string; label: string; realtimeId: number; accumulatedId: number; description?: string | null; special?: boolean; mappedNodeCount?: number; memberPowerIds?: number[] };
export type EnergyNodeLive = { nodeId: number; status: string; checkedAt?: string | null; currentPowerW?: number | null; currentEnergyKwh?: number | null; switchState?: boolean | null; deviceName?: string | null; powerDeviceName?: string | null; energyDeviceName?: string | null; switchDeviceName?: string | null; dead?: boolean | null; enabled?: boolean | null; error?: string | null };
export type EnergyAggregateLive = { key: string; status: string; currentPowerW?: number | null; currentEnergyKwh?: number | null; error?: string | null };
export type Hc3EnergyDevice = { id: number; name?: string | null; type?: string | null; baseType?: string | null; parentId?: number | null; roomId?: number | null; manufacturer?: string | null; model?: string | null; value?: unknown; powerW?: number | null; energyKwh?: number | null; switchState?: boolean | null; hasPower?: boolean; hasEnergy?: boolean; hasSwitch?: boolean; dead?: boolean | null; enabled?: boolean | null; visible?: boolean | null };
export type Hc3EnergyDevicesResponse = { source: string; error?: string | null; count: number; devices: Hc3EnergyDevice[] };
export type EnergyNodesLiveResponse = { checkedAt: string; configured: boolean; nodes: Record<string, EnergyNodeLive>; aggregateMeters?: Record<string, EnergyAggregateLive> };
export type EnergyNode = { id: number; name: string; circuitNo?: number | null; parentNodeId?: number | null; nodeType: string; manufacturer?: string | null; model?: string | null; deviceType?: string | null; hc3DeviceId?: number | null; hc3PowerDeviceId?: number | null; hc3EnergyDeviceId?: number | null; hc3SwitchDeviceId?: number | null; aggregateGroupKey?: string | null; aggregateMeter?: EnergyAggregateMeter | null; endpointKey?: string | null; hasMeter: boolean; hasSwitch: boolean; area?: string | null; active: boolean; note?: string | null; loadCount: number; activeLoadCount: number; expectedPowerW: number; currentPowerW?: number | null; switchState?: boolean | null; liveStatus?: string | null; liveCheckedAt?: string | null; topologyWarning?: string | null; loads: EnergyLoadItem[]; children: EnergyNode[] };
export type EnergyCircuit = { key: string; circuitNo?: number | null; description?: string | null; breaker?: string | null; breakerType?: string | null; status?: string | null; isSunbed: boolean; note?: string | null; loadCount: number; activeLoadCount: number; nodeCount: number; expectedPowerW: number; currentPowerW?: number | null; measuredLoadCount: number; unmeasuredLoadCount: number; measurementMode: string; measurementDetail: string; directLoads: EnergyLoadItem[]; nodes: EnergyNode[] };
export type EnergyCircuitLoadsData = { canManage?: boolean; summary: JsonRecord; aggregateMeters: EnergyAggregateMeter[]; circuits: EnergyCircuit[] };
