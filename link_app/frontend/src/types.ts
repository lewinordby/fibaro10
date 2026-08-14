export type KobleReviewMatch = {
  id: number;
  parkingStartAt?: string | null;
  sunStartedAt?: string | null;
  deltaMinutes?: number | null;
  roomLabel?: string | null;
  userName?: string | null;
  durationMinutes?: number | null;
  paidAmountKr?: number | null;
  feeIncVat?: number | null;
  sourceSystem?: string | null;
};
export type KobleReviewCandidate = {
  id: number;
  status: string;
  confidence: number;
  assessment?: string | null;
  plate: string;
  sun2Id: string;
  vehicleName?: string | null;
  vehicleArea?: string | null;
  userName?: string | null;
  matchesCount: number;
  parkingMatchCount: number;
  matchDaysCount: number;
  plateCandidateCount: number;
  sun2CandidateCount: number;
  competitorMatchesCount: number;
  firstMatchAt?: string | null;
  lastMatchAt?: string | null;
  avgDeltaMinutes?: number | null;
  parkingCount?: number | null;
  paidTotal?: number | null;
  matchedPaidTotal?: number | null;
  note?: string | null;
  path?: string | null;
  matches: KobleReviewMatch[];
};

export type KobleQualifiedRow = {
  id: number;
  status: string;
  confidence: number;
  plate: string;
  sun2Id: string;
  vehicleName?: string | null;
  vehicleArea?: string | null;
  userName?: string | null;
  matchesCount: number;
  parkingMatchCount: number;
  matchDaysCount: number;
  lastMatchAt?: string | null;
  avgDeltaMinutes?: number | null;
  parkingCount?: number | null;
  paidTotal?: number | null;
  matchedPaidTotal?: number | null;
  path?: string | null;
};

export type KobleQualifiedSun2Row = KobleQualifiedRow & {
  sun2VehicleCount: number;
  parkingWithoutSunCount: number;
  parkingMatchShare: number;
};

export type KobleReviewData = {
  generatedAt?: string | null;
  workerStatus?: string | null;
  workerDetail?: string | null;
  workerSeenAt?: string | null;
  generation: number;
  minMatches: number;
  maxMinutes: number;
  visibleCandidateCount: number;
  candidateCount: number;
  strongCandidateCount: number;
  rawPairCount?: number;
  rawOneOffPairCount?: number;
  processedCount: number;
  matchedCount: number;
  qualifiedPlateCount?: number;
  qualifiedPairCount?: number;
  qualifiedPaidTotal?: number;
  qualifiedMatchedPaidTotal?: number;
  qualifiedSun2Rows?: KobleQualifiedSun2Row[];
  qualifiedRows?: KobleQualifiedRow[];
  candidates: KobleReviewCandidate[];
};
