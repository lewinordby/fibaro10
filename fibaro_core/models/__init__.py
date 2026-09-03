"""Public models grouped by domain; no application import or startup side effects."""

from .building import (
    OutdoorLightEvent,
    OutdoorLightSample,
    VentilationEvent,
    VentilationSample,
    YrForecastSample,
    GenericEvent,
    DoorEvent,
    DoorSensorStatus,
    AlarmEvent,
    ControlConfig,
    ControlConfigHistory,
)

from .cleaning import (
    RoborockRobot,
    RoborockStatusSample,
    RoborockTelemetrySample,
    RoborockTelemetryEvent,
    RoborockCleanJob,
    RoborockSchedule,
    RoborockScheduleSnapshot,
    CleaningZone,
    RoborockCleaningZoneMapping,
    RoborockCleaningProfile,
    RoborockDoorAutomation,
    RoborockConsumableSnapshot,
    RoborockMapSnapshot,
    RoborockProbeResult,
    RoborockSyncRun,
    RoborockCommandRun,
)

from .energy import (
    EnergyHourlyConsumption,
    EnergyImportRun,
    EnergyFibaroSample,
    EnergyCircuit,
    EnergyNode,
    EnergyLoad,
    Hc3MeterReading,
)

from .finance import (
    SettlementImport,
    ForecastSnapshot,
)

from .linking import (
    ParkingSunLinkJobState,
    ParkingSunLinkProcessed,
    ParkingSunLinkMatch,
    ParkingSunLinkCandidate,
)

from .maintenance import (
    SiteVisit,
    MaintenanceLogEntry,
)

from .parking import (
    ParkingSession,
    ParkingVehicle,
    ParkingVehicleDetails,
)

from .sun import (
    Sun2RoomDailyStat,
    Sun2ImportRun,
    Sun2TanningSession,
    Sun2TanningSessionImage,
    Sun2Bed,
    Sun2Member,
    Sun2ProductSale,
    Sun2FinanceSettlement,
    Sun2SessionImportRun,
)

from .system import (
    OperationalIncidentReview,
    AssetRegistryItem,
    AutomationWorkbenchRule,
    ImportJobStatus,
    ImportJobRun,
    AiQueryLog,
    AccessKey,
    AuthSession,
    NotificationOutbox,
    AccessLog,
)

__all__ = [
    "AccessKey",
    "AccessLog",
    "AiQueryLog",
    "AlarmEvent",
    "AssetRegistryItem",
    "AuthSession",
    "AutomationWorkbenchRule",
    "CleaningZone",
    "ControlConfig",
    "ControlConfigHistory",
    "DoorEvent",
    "DoorSensorStatus",
    "EnergyCircuit",
    "EnergyFibaroSample",
    "EnergyHourlyConsumption",
    "EnergyImportRun",
    "EnergyLoad",
    "EnergyNode",
    "ForecastSnapshot",
    "GenericEvent",
    "Hc3MeterReading",
    "ImportJobRun",
    "ImportJobStatus",
    "MaintenanceLogEntry",
    "NotificationOutbox",
    "OperationalIncidentReview",
    "OutdoorLightEvent",
    "OutdoorLightSample",
    "ParkingSession",
    "ParkingSunLinkCandidate",
    "ParkingSunLinkJobState",
    "ParkingSunLinkMatch",
    "ParkingSunLinkProcessed",
    "ParkingVehicle",
    "ParkingVehicleDetails",
    "RoborockCleanJob",
    "RoborockCleaningProfile",
    "RoborockCleaningZoneMapping",
    "RoborockCommandRun",
    "RoborockConsumableSnapshot",
    "RoborockDoorAutomation",
    "RoborockMapSnapshot",
    "RoborockProbeResult",
    "RoborockRobot",
    "RoborockSchedule",
    "RoborockScheduleSnapshot",
    "RoborockStatusSample",
    "RoborockSyncRun",
    "RoborockTelemetryEvent",
    "RoborockTelemetrySample",
    "SettlementImport",
    "SiteVisit",
    "Sun2Bed",
    "Sun2FinanceSettlement",
    "Sun2ImportRun",
    "Sun2Member",
    "Sun2ProductSale",
    "Sun2RoomDailyStat",
    "Sun2SessionImportRun",
    "Sun2TanningSession",
    "Sun2TanningSessionImage",
    "VentilationEvent",
    "VentilationSample",
    "YrForecastSample",
]
