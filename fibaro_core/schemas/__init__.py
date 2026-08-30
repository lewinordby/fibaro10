"""Public schemas grouped by domain; no application import or startup side effects."""

from .building import (
    LegacyLogIn,
    EventDataIn,
    DoorEventIn,
)

from .cleaning import (
    RoborockIngestIn,
    RoborockTelemetryIn,
    RoborockControlIn,
    RoborockCleaningProfileIn,
    RoborockDoorAutomationIn,
)

from .energy import (
    Hc3MeterReadingIn,
    EnergyFibaroIn,
    V2EnergyCircuitUpdate,
    V2EnergyNodeIn,
    V2EnergyLoadIn,
)

from .linking import (
    ParkingSunLinkSettingsUpdate,
    ParkingSunLinkCandidateUpdate,
    ParkingSunLinkWorkerStatusIn,
    ParkingSunLinkProcessedIn,
    ParkingSunLinkMatchIn,
    ParkingSunLinkWorkerResultsIn,
)

from .maintenance import (
    MaintenanceLogInput,
    MaintenanceSiteVisitInput,
)

from .parking import (
    ParkingVehicleNameUpdate,
    ParkingVehicleAreaUpdate,
    ParkingVehicleCarInfoUpdate,
)

from .sun import (
    Sun2RoomStatIn,
    Sun2RoomStatsIngestIn,
    Sun2TanningSessionIn,
    Sun2TanningSessionsIngestIn,
    Sun2BedIn,
    Sun2BedsIngestIn,
    Sun2MemberIn,
    Sun2MembersIngestIn,
    Sun2ProductSaleIn,
    Sun2ProductSalesIngestIn,
    Sun2FinanceSettlementIn,
    Sun2FinanceSettlementsIngestIn,
)

from .system import (
    AssetRegistryInput,
    AutomationWorkbenchInput,
    ImportStatusReportIn,
    V2AccessUserCreate,
    V2AccessUserUpdate,
)

__all__ = [
    "AssetRegistryInput",
    "AutomationWorkbenchInput",
    "DoorEventIn",
    "EnergyFibaroIn",
    "EventDataIn",
    "Hc3MeterReadingIn",
    "ImportStatusReportIn",
    "LegacyLogIn",
    "MaintenanceLogInput",
    "MaintenanceSiteVisitInput",
    "ParkingSunLinkCandidateUpdate",
    "ParkingSunLinkMatchIn",
    "ParkingSunLinkProcessedIn",
    "ParkingSunLinkSettingsUpdate",
    "ParkingSunLinkWorkerResultsIn",
    "ParkingSunLinkWorkerStatusIn",
    "ParkingVehicleAreaUpdate",
    "ParkingVehicleCarInfoUpdate",
    "ParkingVehicleNameUpdate",
    "RoborockCleaningProfileIn",
    "RoborockControlIn",
    "RoborockDoorAutomationIn",
    "RoborockIngestIn",
    "RoborockTelemetryIn",
    "Sun2BedIn",
    "Sun2BedsIngestIn",
    "Sun2FinanceSettlementIn",
    "Sun2FinanceSettlementsIngestIn",
    "Sun2MemberIn",
    "Sun2MembersIngestIn",
    "Sun2ProductSaleIn",
    "Sun2ProductSalesIngestIn",
    "Sun2RoomStatIn",
    "Sun2RoomStatsIngestIn",
    "Sun2TanningSessionIn",
    "Sun2TanningSessionsIngestIn",
    "V2AccessUserCreate",
    "V2AccessUserUpdate",
    "V2EnergyCircuitUpdate",
    "V2EnergyLoadIn",
    "V2EnergyNodeIn",
]
