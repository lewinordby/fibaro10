from typing import Any, Dict, List, Literal, TypedDict


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


class HealthAppPayload(TypedDict):
    version: str
    build: str
    commit: str
    startedAt: str


class HealthCheckPayload(TypedDict, total=False):
    status: str
    detail: str


class HealthSourcePayload(TypedDict, total=False):
    jobName: str
    title: str
    label: str
    status: str
    detail: str
    ageMinutes: float | None


class HealthPayload(TypedDict):
    status: HealthStatus
    app: HealthAppPayload
    checks: Dict[str, HealthCheckPayload]
    sources: List[HealthSourcePayload]
    storage: List[str]


JsonPayload = Dict[str, Any]
