from typing import Any, Dict, List, Literal, NotRequired, TypedDict


HealthStatus = Literal["ok", "warn", "bad"]


class BuildLogEntryPayload(TypedDict):
    version: str
    build: str
    date: str
    headline: str
    title: str
    description: str
    applications: List[str]
    changes: List[str]
    request: str
    workDuration: str
    creditsUsed: str
    path: str
    isCurrent: bool


class BuildLogResponsePayload(TypedDict):
    currentBuild: str
    rows: List[BuildLogEntryPayload]


class BuildLogTableRowPayload(TypedDict):
    build: str
    date: str
    headline: str
    title: str
    description: str
    applications: str
    request: str
    work_duration: str
    credits_used: str
    path: str


class ModuleCardPayload(TypedDict):
    title: str
    value: str
    unit: str
    detail: str
    tone: str
    href: NotRequired[str]


class ModuleTablePayload(TypedDict):
    title: str
    columns: List[str]
    rows: List[Dict[str, Any]]
    edit: NotRequired[Dict[str, Any]]


class ModulePayload(TypedDict, total=False):
    title: str
    subtitle: str
    cards: List[ModuleCardPayload]
    charts: List[Dict[str, Any]]
    tables: List[ModuleTablePayload]
    actions: List[Dict[str, Any]]
    filters: List[Dict[str, Any]]


class HealthAppPayload(TypedDict):
    version: str
    build: str
    commit: str
    startedAt: str


class HealthCheckPayload(TypedDict, total=False):
    status: str
    detail: str


class HealthSourcePayload(TypedDict, total=False):
    sourceNo: int | None
    jobName: str
    title: str
    label: str
    category: str
    source: str
    status: str
    statusText: str
    detail: str
    ageMinutes: float | None
    lastRunAt: str | None
    lastSuccessAt: str | None
    lastFailedAt: str | None
    nextExpectedAt: str | None
    recordsImported: int | None
    recordsTotal: int | None
    durationSeconds: float | None
    message: str


class HealthSummarySourcesPayload(TypedDict):
    total: int
    ok: int
    warn: int
    bad: int
    unknown: int


class HealthSummaryPayload(TypedDict):
    sources: HealthSummarySourcesPayload


class HealthPayload(TypedDict):
    status: HealthStatus
    app: HealthAppPayload
    checks: Dict[str, HealthCheckPayload]
    summary: HealthSummaryPayload
    sources: List[HealthSourcePayload]
    storage: List[str]


JsonPayload = Dict[str, Any]
