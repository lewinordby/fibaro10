"""Compose the core API and worker from explicit domain dependencies."""
from dotenv import load_dotenv

load_dotenv()

from fibaro_core.services.forecasts import builders as forecast_builders
from datetime import datetime, timezone
from typing import Any, Dict
import asyncio
import logging

from fastapi import FastAPI
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from microapp_backend import PwaConfig, register_pwa, render_login_page
from microapp_backend.auth import AUTH_SESSION_COOKIE_NAME, clear_auth_cookies, request_is_secure, set_auth_session_cookie
from fibaro_core.catalog import (
    ADMIN_TASK_SEVERITY_SORT,
    AI_CONFIG_KEY,
    AXIS_SNAPSHOT_FILENAME_RE,
    AXIS_SNAPSHOT_ID_RE,
    CONFIG_DEFINITIONS,
    CONTROL_DEVICES,
    DAY_ZOOM_OPTIONS,
    DOOR_SENSOR_CONFIG,
    DOOR_SENSOR_IDS,
    EASYPARK_REQUIRED_COLUMNS,
    ENERGY_ACCUMULATED_ID_BY_POWER_ID,
    ENERGY_ACCUMULATED_KEYS,
    ENERGY_AGGREGATE_GROUP_BY_POWER_ID,
    ENERGY_AGGREGATE_HC3_MEMBERS,
    ENERGY_AGGREGATE_METERS,
    ENERGY_AGGREGATE_METERS_BY_KEY,
    ENERGY_AGGREGATE_POWER_MEMBERS,
    ENERGY_CIRCUIT_SEED_ROWS,
    ENERGY_CIRCUIT_SEED_SOURCE,
    ENERGY_FIBARO_AREAS,
    ENERGY_HC3_HOURLY_DISPLAY_OFFSET,
    ENERGY_HOURLY_COMPARE_FIELDS,
    ENERGY_LOAD_POWER_PROFILES,
    ENERGY_NODE_TYPES,
    ENERGY_REALTIME_MAX_DELTA_SECONDS,
    ENERGY_SUB_KEYS,
    LIGHT_TIMELINE_DEVICES,
    MAINTENANCE_ACTION_OPTIONS,
    MAINTENANCE_PRESENCE_OPTIONS,
    MAINTENANCE_PRIORITY_OPTIONS,
    MAINTENANCE_STATUS_OPTIONS,
    MAINTENANCE_TAG_OPTIONS,
    MAINTENANCE_TARGET_OPTIONS,
    MOBILE_PREVIEW_MONEY_KEYS,
    MOBILE_PREVIEW_SCREENS,
    PARKING_OCCUPANCY_SCALE_MAX,
    PARKING_SUN_LINK_CONFIRMED,
    PARKING_SUN_LINK_PENDING,
    PARKING_SUN_LINK_REJECTED,
    PARKING_SUN_LINK_STATUSES,
    PARKING_TIMELINE_CAPACITY,
    PARKING_TIMELINE_ROWS,
    PARKING_TIME_PERIOD_OPTIONS,
    PARKING_TIME_WEEKDAYS,
    PARKING_WEEKLY_AVERAGE_PERIOD_OPTIONS,
    ROBOROCK_DOOR_AUTOMATION_POLL_SECONDS,
    ROOF_EXHAUST_UNMETERED_W,
    SOLROOM_DOOR_HC3,
    SUNBED_ANALYSIS_VENTILATION_MATCH_SECONDS,
    VENT_TIMELINE_DEVICES,
    WEATHER_LABELS,
    YR_FORECAST_ASSIGNMENTS,
)
from fibaro_core.settings import (
    ACCESS_FAILED_DISABLE_THRESHOLD,
    ACCESS_LOG_FAILURE_RETENTION_DAYS,
    ACCESS_LOG_SUCCESS_RETENTION_DAYS,
    ALARM_APP_URL,
    APP_COMMIT,
    AUTH_COOKIE_NAME,
    AUTH_SESSION_HEADER_NAME,
    AUTH_SESSION_MAX_AGE_SECONDS,
    AUTH_SESSION_RETENTION_DAYS,
    AUTH_USER_COOKIE_NAME,
    CARS_DAY_CACHE_TTL,
    CARS_HISTORY_CACHE_TTL,
    CAR_INFO_APP_TOKEN,
    CAR_INFO_AUTO_TRIGGER_ENABLED,
    CAR_INFO_AUTO_TRIGGER_MAX_PER_SVV_RUN,
    CAR_INFO_CANDIDATE_RETRY_HOURS,
    CAR_INFO_CANDIDATE_TRANSIENT_RETRY_MINUTES,
    CAR_INFO_LOOKUP_TIMEOUT_SECONDS,
    CAR_INFO_LOOKUP_URL,
    DATABASE_URL,
    DREAME_CONTROL_TOKEN,
    DREAME_EXPECTED_ROBOT_NAME,
    DREAME_LOGGER_URL,
    EASYPARK_DOWNLOADER_URL,
    FIBARO10_BACKGROUND_TASKS_ENABLED,
    FIBARO10_PROCESS_ROLE,
    FULL_BACKUP_STATUS_PATH,
    HC3_BASE_URL,
    HC3_DOOR_DEBOUNCE_SECONDS,
    HC3_DOOR_OTHER_OPEN_VERIFY_MINUTES,
    HC3_DOOR_POLL_TIMEOUT_SECONDS,
    HC3_DOOR_SOLROOM_CLOSED_VERIFY_MINUTES,
    HC3_DOOR_UNEXPECTED_CHECK_ENABLED,
    HC3_DOOR_UNEXPECTED_CHECK_INITIAL_DELAY_SECONDS,
    HC3_DOOR_UNEXPECTED_CHECK_INTERVAL_SECONDS,
    HC3_DOOR_UNEXPECTED_RECHECK_MINUTES,
    HC3_ENERGY_DEVICE_LIST_CACHE_SECONDS,
    HC3_ENERGY_LIVE_TIMEOUT_SECONDS,
    HC3_PASS,
    HC3_SWITCH_POLL_TIMEOUT_SECONDS,
    HC3_SWITCH_STATUS_CACHE_SECONDS,
    HC3_USER,
    IMPORT_JOB_FAILURE_RETENTION_DAYS,
    IMPORT_JOB_SUCCESS_RETENTION_DAYS,
    KOBLE_WORKER_TOKEN,
    MASTER_ACCESS_KEY_HASH,
    MET_LAT,
    MET_LON,
    MET_USER_AGENT,
    MOBILE_PREVIEW_REFRESH_SECONDS,
    NIGHTLY_BACKUP_STATUS_PATH,
    NOTIFICATION_SENT_RETENTION_DAYS,
    NTFY_ACCESS_COOLDOWN_MINUTES,
    NTFY_ACCESS_TOPIC,
    NTFY_BASE_URL,
    NTFY_BOLLARDS_TOPIC,
    NTFY_DOORS_TOPIC,
    NTFY_LIGHTS_TOPIC,
    NTFY_OUTBOX_POLL_SECONDS,
    NTFY_OUTBOX_RETRY_BASE_SECONDS,
    NTFY_OUTBOX_RETRY_MAX_SECONDS,
    NTFY_OUTBOX_STALE_LOCK_SECONDS,
    NTFY_TIMEOUT_SECONDS,
    NTFY_VENTILATION_TOPIC,
    OPENAI_MODEL,
    OPERATIONAL_RETENTION_ENABLED,
    OPERATIONAL_RETENTION_INITIAL_DELAY_SECONDS,
    OPERATIONAL_RETENTION_INTERVAL_HOURS,
    OPERATIONAL_RETENTION_POLICY,
    OWNTRACKS_LILLETORGET_WAYPOINTS,
    OWNTRACKS_SERVICE_URL,
    OWNTRACKS_SITE_VISIT_LOCATION_KEY,
    OWNTRACKS_SITE_VISIT_LOCATION_NAME,
    OWNTRACKS_VISIT_SYNC_ENABLED,
    OWNTRACKS_VISIT_SYNC_INTERVAL_SECONDS,
    OWNTRACKS_VISIT_SYNC_LOOKBACK_HOURS,
    OWNTRACKS_VISIT_SYNC_TIMEOUT_SECONDS,
    PUBLIC_PATHS,
    PUBLIC_PREFIXES,
    ROBOROCK_CONTROL_TOKEN,
    ROBOROCK_LOGGER_URL,
    SECURITY_HSTS_ENABLED,
    SECURITY_HSTS_MAX_AGE_SECONDS,
    SITE_VISIT_ACTIVE_MAX_HOURS,
    SITE_VISIT_MAINTENANCE_LINK_MARGIN_MINUTES,
    SLOW_REQUEST_WARNING_MS,
    SUMMARY_CACHE_TTL,
    SUN2_AXIS_SNAPSHOT_DAY_CACHE_ARCHIVE_SECONDS,
    SUN2_AXIS_SNAPSHOT_DAY_CACHE_CURRENT_SECONDS,
    SUN2_AXIS_SNAPSHOT_LINK_DAYS,
    SUN2_AXIS_SNAPSHOT_LINK_ENABLED,
    SUN2_AXIS_SNAPSHOT_LINK_INITIAL_DELAY_SECONDS,
    SUN2_AXIS_SNAPSHOT_LINK_INTERVAL_SECONDS,
    SUN2_AXIS_SNAPSHOT_LINK_LIMIT,
    SUN2_AXIS_SNAPSHOT_MINUTE_ASSUMED_SECOND,
    SUN2_AXIS_SNAPSHOT_ROOT,
    SUN2_AXIS_SNAPSHOT_SERIES_OFFSETS_SECONDS,
    SUN2_AXIS_SNAPSHOT_TOLERANCE_SECONDS,
    SUN2_SESSIONS_QUIET_END_HOUR,
    SUN2_SESSIONS_QUIET_START_HOUR,
    SUN2_SESSION_SCRAPER_URL,
    SUNBED_POWER_ANALYSIS_CACHE_TTL,
    SUNBED_POWER_CACHE_WARM_ENABLED,
    SUNROOM_DOOR_ALERT_AFTER_END_MINUTES,
    SUNROOM_DOOR_CRITICAL_MINUTES,
    SUNROOM_DOOR_EXIT_GRACE_MINUTES,
    SUNROOM_DOOR_FAN_AFTER_RUN_MINUTES,
    SUNROOM_DOOR_FORCED_SYNC_MINUTES,
    SUNROOM_DOOR_MONITOR_ENABLED,
    SUNROOM_DOOR_MONITOR_INITIAL_DELAY_SECONDS,
    SUNROOM_DOOR_MONITOR_INTERVAL_SECONDS,
    SUNROOM_DOOR_NEW_SESSION_GRACE_MINUTES,
    SUNROOM_DOOR_NO_SESSION_ALARM_MINUTES,
    SUNROOM_DOOR_PAYMENT_DELAY_MINUTES,
    SUNROOM_DOOR_SESSION_GRACE_MINUTES,
    SUNROOM_DOOR_SESSION_LOOKBACK_HOURS,
    SUNROOM_DOOR_SYNC_FAILURE_ALARM_MINUTES,
    SUNROOM_DOOR_SYNC_MAX_ATTEMPTS,
    SUNROOM_DOOR_SYNC_MIN_INTERVAL_SECONDS,
    SUNROOM_DOOR_SYNC_TIMEOUT_SECONDS,
    SUNROOM_DOOR_WARN_AFTER_END_MINUTES,
    SUNROOM_BED_STATUS_MAX_AGE_MINUTES,
    SVV_API_AUTH_HEADER,
    SVV_API_AUTH_PREFIX,
    SVV_API_KEY,
    SVV_API_URL,
    SVV_IMPORT_SYNC_BATCH_SIZE,
    SVV_PERMANENT_NO_DATA_STATUSES,
    SVV_RETRY_AFTER_HOURS,
    SVV_SYNC_BATCH_SIZE,
    SVV_SYNC_ENABLED,
    SVV_SYNC_INTERVAL_MINUTES,
    SVV_TRANSIENT_RETRY_AFTER_MINUTES,
    SVV_TRANSIENT_STATUSES,
    UNIFI_PROTECT_API_TIMEOUT_SECONDS,
    UNIFI_PROTECT_EVENTS_URL,
    UNIFI_PROTECT_READ_API_TOKEN,
    env_float,
)
from fibaro_core.database import Base, create_database
from fibaro_core.runtime_state import IncidentState, ProcessLocks
from fibaro_core.services.comparisons.overview import overview_comparison_plan, load_overview_comparisons, build_overview_cards
from fibaro_core.services.comparisons.windows import (
    import_row_stamp,
    source_as_of,
    period_cutoff,
    shifted_period_cutoff,
    cutoff_label,
    parse_anchor_day,
    iso_week_start,
    same_iso_week_previous_year,
    week_label,
    status_navigation,
    selected_period_cutoff,
    status_comparison_windows,
    status_period_summary,
    status_timeline_ticks,
    status_timeline_position,
)
from fibaro_core.services.comparisons.chart import build_status_comparison
from fibaro_core.services.comparisons.years import (
    YEAR_COMPARISON_COLORS, build_sun2_year_comparison, build_parking_year_comparison, build_revenue_year_comparison,
)
from fibaro_core.services.summaries.energy import (
    add_energy_row_to_summary,
    add_fast_energy_summary,
    build_energy_summaries,
    build_energy_summaries_fast,
    empty_energy_summary,
    empty_fast_energy_summary,
    energy_sum_columns,
    finalize_energy_summary,
    finalized_energy_aggregate,
)
from fibaro_core.services.summaries.parking import (
    build_parking_summaries_fast,
    empty_parking_summary,
    parking_daily_by_year,
    parking_datetime_snapshot,
    parking_datetime_snapshots,
    parking_weekly_items,
    parking_year_comparison_delta,
    parking_year_series,
)
from fibaro_core.services.summaries.periods import (
    add_months,
    days_in_year,
    iso_week_period,
    month_label,
    normalized_stat_date,
    parse_anchor_year,
    year_comparison_navigation,
)
from fibaro_core.services.summaries.revenue import (
    combine_business_summaries,
    count_day_rank_summary,
    count_period_rank_summary,
    period_rank_summary,
    revenue_daily_by_year,
    revenue_day_rank_summary,
    revenue_period_rank_summary,
    revenue_year_comparison_delta,
    revenue_year_series,
)
from fibaro_core.services.summaries.sun import (
    SUN2_SUM_FIELDS,
    add_fast_sun2_summary,
    add_sun2_row_to_summary,
    build_sun2_summaries,
    build_sun2_summaries_fast,
    empty_fast_sun2_summary,
    empty_sun2_summary,
    finalize_sun2_summary,
    finalized_sun2_aggregate,
    sun2_daily_by_year,
    sun2_datetime_snapshot,
    sun2_datetime_snapshots,
    sun2_period_snapshot,
    sun2_period_snapshots,
    sun2_sum_columns,
    sun2_weekly_items,
    sun2_year_comparison_delta,
    sun2_year_series,
)
from fibaro_core.config import SUN2_AXIS_SNAPSHOT_OFFSET_SECONDS
from fibaro_core.models import (
    AccessKey,
    AccessLog,
    AiQueryLog,
    AlarmEvent,
    AssetRegistryItem,
    AuthSession,
    AutomationWorkbenchRule,
    CleaningZone,
    ControlConfig,
    ControlConfigHistory,
    DoorEvent,
    EnergyCircuit,
    EnergyFibaroSample,
    EnergyHourlyConsumption,
    EnergyImportRun,
    EnergyLoad,
    EnergyNode,
    ForecastSnapshot,
    GenericEvent,
    Hc3MeterReading,
    ImportJobRun,
    ImportJobStatus,
    MaintenanceLogEntry,
    NotificationOutbox,
    OperationalIncidentReview,
    OutdoorLightEvent,
    OutdoorLightSample,
    ParkingSession,
    ParkingSunLinkCandidate,
    ParkingSunLinkJobState,
    ParkingSunLinkMatch,
    ParkingSunLinkProcessed,
    ParkingVehicle,
    ParkingVehicleDetails,
    RoborockCleanJob,
    RoborockCleaningProfile,
    RoborockCleaningZoneMapping,
    RoborockCommandRun,
    RoborockConsumableSnapshot,
    RoborockDoorAutomation,
    RoborockMapSnapshot,
    RoborockProbeResult,
    RoborockRobot,
    RoborockSchedule,
    RoborockScheduleSnapshot,
    RoborockStatusSample,
    RoborockSyncRun,
    RoborockTelemetryEvent,
    RoborockTelemetrySample,
    SettlementImport,
    SiteVisit,
    Sun2Bed,
    Sun2FinanceSettlement,
    Sun2ImportRun,
    Sun2Member,
    Sun2ProductSale,
    Sun2RoomDailyStat,
    Sun2SessionImportRun,
    Sun2TanningSession,
    Sun2TanningSessionImage,
    VentilationEvent,
    VentilationSample,
    YrForecastSample,
)
from fibaro_core.schemas import (
    AssetRegistryInput,
    AutomationWorkbenchInput,
    DoorEventIn,
    EnergyFibaroIn,
    EventDataIn,
    Hc3MeterReadingIn,
    ImportStatusReportIn,
    LegacyLogIn,
    MaintenanceLogInput,
    MaintenanceSiteVisitInput,
    ParkingSunLinkCandidateUpdate,
    ParkingSunLinkMatchIn,
    ParkingSunLinkProcessedIn,
    ParkingSunLinkSettingsUpdate,
    ParkingSunLinkWorkerResultsIn,
    ParkingSunLinkWorkerStatusIn,
    ParkingVehicleAreaUpdate,
    ParkingVehicleCarInfoUpdate,
    ParkingVehicleNameUpdate,
    RoborockCleaningProfileIn,
    RoborockControlIn,
    RoborockDoorAutomationIn,
    RoborockIngestIn,
    RoborockTelemetryIn,
    Sun2BedIn,
    Sun2BedsIngestIn,
    Sun2FinanceSettlementIn,
    Sun2FinanceSettlementsIngestIn,
    Sun2MemberIn,
    Sun2MembersIngestIn,
    Sun2ProductSaleIn,
    Sun2ProductSalesIngestIn,
    Sun2RoomStatIn,
    Sun2RoomStatsIngestIn,
    Sun2TanningSessionIn,
    Sun2TanningSessionsIngestIn,
    V2AccessUserCreate,
    V2AccessUserUpdate,
    V2EnergyCircuitUpdate,
    V2EnergyLoadIn,
    V2EnergyNodeIn,
)
from fibaro_core.export_definitions import (
    LIGHT_COLUMNS,
    LIGHT_SAMPLE_COLUMNS,
    VENT_COLUMNS,
    GENERIC_COLUMNS,
    DOOR_EVENT_COLUMNS,
    VENT_SAMPLE_COLUMNS,
    YR_SAMPLE_COLUMNS,
    YR_LOG_TABLE_COLUMNS,
    ROBOROCK_ROBOT_COLUMNS,
    ROBOROCK_STATUS_COLUMNS,
    ROBOROCK_TELEMETRY_COLUMNS,
    ROBOROCK_TELEMETRY_EVENT_COLUMNS,
    ROBOROCK_TELEMETRY_DISPLAY_FIELDS,
    ROBOROCK_JOB_COLUMNS,
    ROBOROCK_SCHEDULE_COLUMNS,
    ROBOROCK_MAP_COLUMNS,
    SUN2_ROOM_COLUMNS,
    SUN2_IMPORT_COLUMNS,
    SUN2_SESSION_COLUMNS,
    SUN2_SESSION_IMAGE_COLUMNS,
    SUN2_BED_COLUMNS,
    SUN2_MEMBER_COLUMNS,
    SUN2_PRODUCT_SALE_COLUMNS,
    SUN2_FINANCE_SETTLEMENT_COLUMNS,
    SUN2_SESSION_IMPORT_COLUMNS,
    ENERGY_HOURLY_COLUMNS,
    ENERGY_IMPORT_COLUMNS,
    ENERGY_FIBARO_COLUMNS,
    AI_QUERY_COLUMNS,
    AI_DATASETS,
)
from fibaro_core.schema_bootstrap import (
    STARTUP_COLUMNS,
    PERFORMANCE_INDEXES,
)
from fibaro_core.services.assets import (
    asset_registry_payload,
    apply_asset_registry_input,
)
from fibaro_core.routers.assets import create_assets_router
from fibaro_core.services.automations import (
    workbench_json_text,
    automation_workbench_payload,
    workbench_config,
    apply_automation_workbench_input,
)
from fibaro_core.routers.automations import create_automations_router
from application_lifecycle import BackgroundTaskSupervisor, create_lifespan
from build_log import APP_BUILD, APP_VERSION, BUILD_LOG, api_build_log_row, build_log_entry_by_build, normalized_build_log_entry
from api_contracts import admin_build_payload, admin_builds_payload
from api_types import ModuleCardPayload, ModuleTablePayload
from cars_domain import (
    cars_confidence_level,
    cars_daily_payment_metrics,
    cars_detection_is_covered,
    cars_group_daily_recognitions,
    cars_likely_ocr_variants,
    cars_plate_edit_distance,
    cars_public_detection,
    cars_recognition_local_datetime,
    cars_unifi_score,
)
from reconciliation_domain import (
    evaluate_reconciliation,
    reconciliation_difference,
    reconciliation_group,
    reconciliation_summary,
    state_reconciliation,
)
from incident_domain import (
    apply_incident_reviews,
    backup_control,
    incident_summary,
    operational_incident,
    parse_status_text,
)
from roborock_zones import RoborockZoneScheduleError, discover_roborock_zone_candidates
from roborock_profiles import (
    CLEANING_TYPE_LABELS,
    DEFAULT_CLEANING_PROFILES,
    cleaning_profile_options,
    cleaning_profile_summary,
    validate_cleaning_profile,
)
from roborock_reports import build_night_report, build_schedule_check, report_window
from roborock_weekly import build_weekly_job_log
from roborock_water import build_water_report
from roborock_refills import build_refill_log, iso_week_start as refill_iso_week_start
from roborock_door_automation import (
    automation_counter_start,
    automation_decision,
    opening_window,
    profile_command_payload,
    unique_ints,
)
from cleaning_robot_domain import (
    CLEANING_ROBOT_STATUS_STALE_AFTER_MINUTES,
    cleaning_robot_is_active,
    cleaning_robot_operational_state,
    cleaning_provider,
    cleaning_provider_label,
    cleaning_robot_external_id,
    cleaning_robot_sort_key,
    cleaning_robot_uid,
    expected_dreame_summary,
)
from energy_helpers import (
    circuit_technical_label,
    energy_circuit_is_sunbed,
    energy_query_url,
    filter_energy_circuits_by_sunbed,
    form_bool,
    form_float,
    form_int,
    form_text,
    normalize_energy_sunbed_filter,
    parse_elvia_json_payload,
)
from import_jobs import IMPORT_JOB_DEFINITIONS, IMPORT_JOB_NUMBER_BY_NAME
from observability import cache_control_for_path, health_payload, response_timing_headers
from operational_retention import OperationalRetentionPolicy, execute_retention_statements
from unifi_protect_client import ProtectLedgerClient, ProtectLedgerError
from pdf_exports import build_table_pdf, pdf_response
from parking_vehicle_helpers import (
    CAR_INFO_IMPORT_JOB_BY_COUNTRY,
    DANISH_LICENSE_PLATE_SQL_REGEX,
    SWEDISH_LICENSE_PLATE_SQL_REGEX,
    car_info_area_label,
    car_info_confirmed_foreign,
    car_info_confirmed_swedish,
    car_info_country_code,
    car_info_field_value,
    car_info_fields,
    car_info_import_job_name,
    car_info_import_ok,
    car_info_lookup_country_code,
    car_info_provider_label,
    car_info_source_label,
    car_info_status_label,
    car_info_vehicle_title,
    code_text,
    compact_plate,
    compact_plate_sql,
    data_path,
    first_value,
    first_vehicle_data,
    foreign_plate_country_code,
    is_danish_license_plate,
    is_supported_foreign_license_plate,
    is_swedish_license_plate,
    normalize_plate,
    parse_date_value,
    parse_float_value,
    parse_int_value,
    parse_svv_datetime_value,
    parking_current_ownership_warning,
    parking_day_time_label,
    parking_duration_minutes,
    parking_row_context,
    parking_slot_remainder_minutes,
    parking_source_label,
    parking_vehicle_display_class,
    parking_vehicle_display_color,
    parking_vehicle_display_inspection_deadline,
    parking_vehicle_display_label,
    parking_vehicle_display_registration_status,
    parking_vehicle_display_source,
    parking_vehicle_display_year,
    parking_vehicle_label,
    parking_vehicle_label_is_unknown,
    parking_vehicle_summary,
    parking_vehicle_year,
    svv_current_ownership_at,
    svv_detail_values,
)
from roborock_domain import (
    cleaning_water_mode_label,
    format_seconds_as_hours,
    roborock_active_cycle_summary,
    roborock_bool_label,
    roborock_charge_label,
    roborock_dock_error_label,
    roborock_dock_type_label,
    roborock_error_label,
    roborock_fan_label,
    roborock_json,
    roborock_job_status,
    roborock_mop_label,
    roborock_next_schedule_text,
    roborock_next_schedule_score,
    roborock_operational_readiness,
    reconcile_roborock_schedule_snapshot,
    roborock_rounds_label,
    roborock_schedule_text,
    roborock_signal_label,
    roborock_state_label,
    roborock_telemetry_changes,
    roborock_telemetry_value_label,
    roborock_water_label,
)
from security import apply_security_headers
from solar_position import solar_elevation_degrees
from system_inventory import (
    system_component_rows,
    system_component_summary,
    system_subsystem_rows,
    system_web_interface_rows,
)
from sun2_helpers import (
    SUN2_ROOM_MAP_BY_DISPLAY,
    SUN2_ROOM_OPTIONS,
    SUN2_ROOM_UNKNOWN_OLD_10,
    normalize_room_id,
    repair_mojibake,
    room_key_from_name,
    sun2_room_identity,
    sun2_room_label,
)
from time_formatting import (
    api_local_iso,
    LOCAL_TZ,
    format_local_datetime,
    format_local_time,
    format_source_datetime,
    format_source_datetime_short,
    format_source_time,
    local_naive_to_utc_naive,
    local_now_naive,
    normalize_local_naive,
    parse_datetime,
    sample_bucket,
    utc_naive_to_local_naive,
)
from unifi_protect import (
    UNIFI_PROTECT_PARKING_CAMERA_ID,
    unifi_protect_parking_timelapse_url,
)
from value_parsing import (
    area_m2_from_payload,
    bool_value,
    first_dict,
    float_or_zero,
    float_value,
    int_or_zero,
    int_value,
    timestamp_value,
)
from v2_navigation import v2_module_title

logger = logging.getLogger("fibaro10")
APP_STARTED_AT = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


MET_WEATHER_CACHE = {"expires": datetime.min, "value": None}

SUMMARY_CACHE: Dict[str, Dict[str, Any]] = {}
hc3_door_unexpected_verified_until: Dict[int, datetime] = {}
OPERATIONAL_RETENTION_STATE: Dict[str, Any] = {
    "status": "waiting" if OPERATIONAL_RETENTION_ENABLED else "disabled",
    "lastRunAt": None,
    "lastSuccessAt": None,
    "lastError": None,
    "deleted": {},
}

axis_snapshot_day_cache: Dict[tuple[str, str], Dict[str, Any]] = {}
sunroom_door_verifications: Dict[str, Dict[str, Any]] = {}

incident_state = IncidentState()
process_locks = ProcessLocks()


background_tasks = BackgroundTaskSupervisor(logger)
app = FastAPI(
    title="Fibaro10",
    lifespan=create_lifespan(lambda: startup(), lambda: shutdown_application()),
)
FIBARO10_PWA = PwaConfig(
    name="Lilletorget Fibaro10",
    short_name="Fibaro10",
    description="Samlet operativ styring, analyse og administrasjon for Lilletorget.",
    theme_color="#4f46e5",
    categories=("business", "productivity", "utilities"),
)
register_pwa(app, FIBARO10_PWA)
app.add_middleware(GZipMiddleware, minimum_size=1024, compresslevel=5)
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")
templates.env.globals.update(app_version=APP_VERSION, app_build=APP_BUILD, build_log=BUILD_LOG)


templates.env.filters["localtime"] = format_local_datetime
templates.env.filters["localtime_short"] = format_local_time
templates.env.filters["source_time"] = format_source_datetime
templates.env.filters["source_time_short"] = format_source_time
templates.env.filters["source_datetime_short"] = format_source_datetime_short


templates.env.filters["roborock_state"] = roborock_state_label
templates.env.filters["roborock_error"] = roborock_error_label
templates.env.filters["roborock_fan"] = roborock_fan_label
templates.env.filters["roborock_mop"] = roborock_mop_label
templates.env.filters["roborock_water"] = roborock_water_label
templates.env.filters["roborock_charge"] = roborock_charge_label
templates.env.filters["roborock_signal"] = roborock_signal_label
templates.env.filters["yesno"] = roborock_bool_label
templates.env.filters["hours"] = format_seconds_as_hours
templates.env.filters["schedule_text"] = roborock_schedule_text
templates.env.filters["rounds"] = roborock_rounds_label
templates.env.filters["pretty_json"] = roborock_json

engine, async_session = create_database(DATABASE_URL)


hc3_switch_status_cache: Dict[int, tuple[float, Dict[str, Any]]] = {}
hc3_energy_device_list_cache: Dict[str, Any] = {}


from fibaro_core.services.presentation import format_short_number


from fibaro_core.services.presentation import format_signed_short_number


from fibaro_core.services.forecasts.calendar import easter_sunday


from fibaro_core.services.forecasts.calendar import norwegian_holiday_name


from fibaro_core.services.forecasts.calendar import month_distance


from fibaro_core.services.forecasts.calendar import iter_dates


from fibaro_core.services.forecasts.calendar import month_end


from fibaro_core.services.forecasts.models import SUN2_FORECAST_SEASON_WEIGHTS
from fibaro_core.services.forecasts.models import PARKING_FORECAST_SEASON_WEIGHTS


from fibaro_core.services.forecasts.models import weighted_average


from fibaro_core.services.forecasts.models import sun2_history_weight


from fibaro_core.services.forecasts.models import sun2_history_weight_precomputed


from fibaro_core.services.forecasts.models import sun2_daily_model


from fibaro_core.services.forecasts.models import sun2_model_history_features


from fibaro_core.services.forecasts.models import sun2_daily_model_from_features


from fibaro_core.services.forecasts.models import sun2_period_actual


from fibaro_core.services.forecasts.models import sun2_apply_tempo


from fibaro_core.services.forecasts.models import parking_apply_period_tempo


from fibaro_core.services.forecasts.models import opening_day_fraction


from fibaro_core.services.forecasts.models import weighted_intraday_fraction


from fibaro_core.services.forecasts.models import sun2_historical_day_fraction


from fibaro_core.services.forecasts.models import parking_historical_day_fraction


from fibaro_core.services.forecasts.models import intraday_forecast_value


from fibaro_core.services.forecasts.models import parking_daily_model


from fibaro_core.services.forecasts.models import parking_model_history_features


from fibaro_core.services.forecasts.models import parking_daily_model_from_features


from fibaro_core.services.forecasts.models import parking_period_actual


from fibaro_core.services.forecasts.models import parking_history_weight


from fibaro_core.services.forecasts.models import parking_history_weight_precomputed


from fibaro_core.services.forecasts.snapshots import forecast_period_label


from fibaro_core.services.forecasts.snapshots import db_naive_utc


from fibaro_core.services.forecasts.snapshots import actual_for_forecast_period


from fibaro_core.services.forecasts.snapshots import forecast_snapshot_from_period


from fibaro_core.services.forecasts.snapshots import save_forecast_snapshots


from fibaro_core.services.forecasts.snapshots import saved_forecast_table


from fibaro_core.services.forecasts.snapshots import forecast_snapshot_history


from fibaro_core.services.forecasts.snapshots import forecast_snapshot_stamp


from fibaro_core.services.forecasts.snapshots import forecast_chart_time_label


templates.env.filters["short_number"] = format_short_number


# HC3 accumulated kWh samples are end-stamped. For hourly comparison against
# Elvia, show the delta on the hour it belongs to, not the hour it was posted.


from fibaro_core.services.presentation import api_table


from fibaro_core.services.presentation import api_table_meta


from fibaro_core.services.presentation import api_chart


from fibaro_core.services.settlements.source_queries import sun2_product_daily_scope_condition


from fibaro_core.services.settlements.source_queries import sun2_product_monthly_scope_condition


from fibaro_core.services.settlements.source_queries import sun2_product_amount_inc_expr


from fibaro_core.services.settlements.source_queries import sun2_product_amount_ex_expr


from fibaro_core.services.presentation import api_card


from fibaro_core.services.presentation import api_iso_value


from fibaro_core.services.settlements.parsing import PARKING_SETTLEMENT_PROVIDER
from fibaro_core.services.settlements.parsing import SUN_SETTLEMENT_PROVIDER
from fibaro_core.services.settlements.mail import PARKING_SETTLEMENT_SENDER
from fibaro_core.services.settlements.parsing import SETTLEMENT_ATTACHMENT_EXTENSIONS
from fibaro_core.services.settlements.parsing import SETTLEMENT_PARSER_VERSION
from fibaro_core.services.settlements.parsing import NORWEGIAN_MONTHS


from fibaro_core.services.settlements.parsing import decoded_mime_header


from fibaro_core.services.settlements.mail import message_email_date


from fibaro_core.services.settlements.mail import settlement_gmail_credentials


from fibaro_core.services.settlements.mail import settlement_mailboxes


from fibaro_core.services.settlements.mail import settlement_gmail_configured


from fibaro_core.services.settlements.mail import select_gmail_mailbox


from fibaro_core.services.settlements.mail import parse_imap_mailbox_name


from fibaro_core.services.settlements.mail import discover_gmail_all_mailbox


from fibaro_core.services.settlements.parsing import is_settlement_attachment


from fibaro_core.services.settlements.parsing import iter_message_attachments


from fibaro_core.services.settlements.parsing import parse_settlement_period


from fibaro_core.services.settlements.parsing import settlement_decode_text


from fibaro_core.services.settlements.parsing import settlement_text_lines


from fibaro_core.services.settlements.parsing import extract_settlement_text


from fibaro_core.services.settlements.parsing import SETTLEMENT_NUMBER_RE


from fibaro_core.services.settlements.parsing import parse_settlement_number


from fibaro_core.services.settlements.parsing import settlement_numbers_from_line


from fibaro_core.services.settlements.parsing import settlement_number_value


from fibaro_core.services.settlements.parsing import settlement_line_source


from fibaro_core.services.settlements.parsing import settlement_parse_date_from_line


from fibaro_core.services.settlements.parsing import parse_parking_settlement_text


from fibaro_core.services.settlements.parsing import parse_parking_settlement_attachment


from fibaro_core.services.settlements.parsing import sun_settlement_number_from_line


from fibaro_core.services.settlements.parsing import SUN_SETTLEMENT_AMOUNT_FIELDS


from fibaro_core.services.settlements.parsing import normalize_sun_creditnote_signs


from fibaro_core.services.settlements.parsing import parse_sun_settlement_text


from fibaro_core.services.settlements.parsing import parse_sun_settlement_attachment


from fibaro_core.services.settlements.parsing import parse_settlement_attachment_for_provider


from fibaro_core.services.settlements.parsing import settlement_period_from_parsed_dates


from fibaro_core.services.settlements.parsing import settlement_public_parsed


from fibaro_core.services.settlements.parsing import settlement_parsed_meta


from fibaro_core.services.settlements.parsing import settlement_parsed_value


from fibaro_core.services.settlements.parsing import settlement_parsed_float


from fibaro_core.services.settlements.parsing import settlement_needs_parse


from fibaro_core.services.settlements.parsing import ensure_settlement_parsed


from fibaro_core.services.settlements.parsing import settlement_field_source


from fibaro_core.services.settlements.parsing import settlement_field_confidence


from fibaro_core.services.settlements.presentation import settlement_row_api


from fibaro_core.services.presentation import format_file_size


from fibaro_core.services.settlements.presentation import settlement_field


from fibaro_core.services.settlements.controls import settlement_sum_or_none


from fibaro_core.services.settlements.presentation import settlement_form_field


from fibaro_core.services.settlements.controls import settlement_source_expected


from fibaro_core.services.settlements.controls import sun2_product_sales_period_summary


from fibaro_core.services.settlements.controls import sun2_product_sales_expected


from fibaro_core.services.settlements.controls import sun2_finance_settlement_period_summary


from fibaro_core.services.settlements.controls import sun2_tanning_revenue_expected


from fibaro_core.services.settlements.controls import sun2_tanning_sessions_revenue_expected


from fibaro_core.services.settlements.controls import sun2_tanning_revenue_control_expected


from fibaro_core.services.settlements.controls import sun2_tanning_sessions_period_summary


from fibaro_core.services.settlements.controls import settlement_form_rows


from fibaro_core.services.settlements.controls import sun_settlement_form_rows


from fibaro_core.services.settlements.presentation import settlement_original_payload


from fibaro_core.services.settlements.presentation import SETTLEMENT_PARSED_FIELD_LABELS


from fibaro_core.services.settlements.presentation import SUN_SETTLEMENT_PARSED_FIELD_LABELS


from fibaro_core.services.settlements.presentation import parsed_field_rows_for_labels


from fibaro_core.services.settlements.presentation import settlement_parsed_field_rows


from fibaro_core.services.settlements.presentation import sun_settlement_parsed_field_rows


from fibaro_core.services.settlements.presentation import settlement_detail_payload


from fibaro_core.services.settlements.presentation import sun_settlement_detail_payload


from fibaro_core.services.settlements.presentation import sun_settlement_summary_row


from fibaro_core.services.settlements.presentation import sun_settlement_module_payload


from fibaro_core.services.settlements.presentation import parking_settlement_module_payload


from fibaro_core.services.settlements.mail import fetch_parking_settlements_from_gmail


from fibaro_core.services.settlements.reconciliation import reconciliation_diff


from fibaro_core.services.settlements.reconciliation import reconciliation_status


from fibaro_core.services.settlements.reconciliation import settlement_amount_sum


from fibaro_core.services.settlements.reconciliation import revenue_settlement_reconciliation_rows


from fibaro_core.services.settlements.source_queries import parking_source_control_key


from fibaro_core.services.settlements.source_queries import parking_period_source_summaries


_roborock_door_automation_lock = asyncio.Lock()


# Domain service composition. Deferred callbacks break cross-domain construction cycles.
from fibaro_core.services.runtime import common as common_services
common_dependencies = common_services.Dependencies(
)
common_service = common_services.create_service(common_dependencies)
average_value = common_service["average_value"]
exact_search_text = common_service["exact_search_text"]
exact_word_match = common_service["exact_word_match"]
is_not_found_marker = common_service["is_not_found_marker"]
json_safe_model_payload = common_service["json_safe_model_payload"]
json_value = common_service["json_value"]
latest_timestamp_from = common_service["latest_timestamp_from"]
minute_bucket = common_service["minute_bucket"]
nested_extra_value = common_service["nested_extra_value"]
normalized_exact_search_text = common_service["normalized_exact_search_text"]
parse_boolish = common_service["parse_boolish"]
parse_optional_date = common_service["parse_optional_date"]
time_minutes = common_service["time_minutes"]
value_from_payload = common_service["value_from_payload"]
from fibaro_core.services.runtime import access as access_services
access_dependencies = access_services.Dependencies(
    ACCESS_FAILED_DISABLE_THRESHOLD=ACCESS_FAILED_DISABLE_THRESHOLD,
    AUTH_SESSION_HEADER_NAME=AUTH_SESSION_HEADER_NAME,
    AUTH_SESSION_MAX_AGE_SECONDS=AUTH_SESSION_MAX_AGE_SECONDS,
    NTFY_ACCESS_COOLDOWN_MINUTES=NTFY_ACCESS_COOLDOWN_MINUTES,
    NTFY_ACCESS_TOPIC=NTFY_ACCESS_TOPIC,
    PUBLIC_PATHS=PUBLIC_PATHS,
    PUBLIC_PREFIXES=PUBLIC_PREFIXES,
    async_session=async_session,
    enqueue_ntfy_message=lambda *args, **kwargs: enqueue_ntfy_message(*args, **kwargs),
    logger=logger,
    mobile_preview_can_view_money=lambda *args, **kwargs: mobile_preview_can_view_money(*args, **kwargs),
)
access_service = access_services.create_service(access_dependencies)
access_key_prefix = access_service["access_key_prefix"]
access_password_hash = access_service["access_password_hash"]
access_role = access_service["access_role"]
access_role_label = access_service["access_role_label"]
api_access_key_edit = access_service["api_access_key_edit"]
api_access_key_row = access_service["api_access_key_row"]
client_ip = access_service["client_ip"]
create_auth_session = access_service["create_auth_session"]
credential_hash = access_service["credential_hash"]
credential_prefix = access_service["credential_prefix"]
find_access_key = access_service["find_access_key"]
find_auth_session = access_service["find_auth_session"]
hash_access_key = access_service["hash_access_key"]
hash_auth_session_token = access_service["hash_auth_session_token"]
is_public_request = access_service["is_public_request"]
log_access_attempt = access_service["log_access_attempt"]
mobile_preview_access_key = access_service["mobile_preview_access_key"]
normalize_username = access_service["normalize_username"]
parse_form_body = access_service["parse_form_body"]
presented_credentials = access_service["presented_credentials"]
presented_session_token = access_service["presented_session_token"]
publish_access_ntfy = access_service["publish_access_ntfy"]
require_master = access_service["require_master"]
require_settings_access = access_service["require_settings_access"]
revoke_auth_session = access_service["revoke_auth_session"]
should_publish_access_ntfy = access_service["should_publish_access_ntfy"]
should_use_secure_cookie = access_service["should_use_secure_cookie"]
wants_html = access_service["wants_html"]
from fibaro_core.services.runtime import sun as sun_services
sun_dependencies = sun_services.Dependencies(
    AXIS_SNAPSHOT_FILENAME_RE=AXIS_SNAPSHOT_FILENAME_RE,
    AXIS_SNAPSHOT_ID_RE=AXIS_SNAPSHOT_ID_RE,
    SUMMARY_CACHE=SUMMARY_CACHE,
    SUN2_AXIS_SNAPSHOT_DAY_CACHE_ARCHIVE_SECONDS=SUN2_AXIS_SNAPSHOT_DAY_CACHE_ARCHIVE_SECONDS,
    SUN2_AXIS_SNAPSHOT_DAY_CACHE_CURRENT_SECONDS=SUN2_AXIS_SNAPSHOT_DAY_CACHE_CURRENT_SECONDS,
    SUN2_AXIS_SNAPSHOT_LINK_DAYS=SUN2_AXIS_SNAPSHOT_LINK_DAYS,
    SUN2_AXIS_SNAPSHOT_LINK_ENABLED=SUN2_AXIS_SNAPSHOT_LINK_ENABLED,
    SUN2_AXIS_SNAPSHOT_LINK_INITIAL_DELAY_SECONDS=SUN2_AXIS_SNAPSHOT_LINK_INITIAL_DELAY_SECONDS,
    SUN2_AXIS_SNAPSHOT_LINK_INTERVAL_SECONDS=SUN2_AXIS_SNAPSHOT_LINK_INTERVAL_SECONDS,
    SUN2_AXIS_SNAPSHOT_LINK_LIMIT=SUN2_AXIS_SNAPSHOT_LINK_LIMIT,
    SUN2_AXIS_SNAPSHOT_MINUTE_ASSUMED_SECOND=SUN2_AXIS_SNAPSHOT_MINUTE_ASSUMED_SECOND,
    SUN2_AXIS_SNAPSHOT_ROOT=SUN2_AXIS_SNAPSHOT_ROOT,
    SUN2_AXIS_SNAPSHOT_SERIES_OFFSETS_SECONDS=SUN2_AXIS_SNAPSHOT_SERIES_OFFSETS_SECONDS,
    SUN2_AXIS_SNAPSHOT_TOLERANCE_SECONDS=SUN2_AXIS_SNAPSHOT_TOLERANCE_SECONDS,
    SUN2_SESSIONS_QUIET_END_HOUR=SUN2_SESSIONS_QUIET_END_HOUR,
    SUN2_SESSION_SCRAPER_URL=SUN2_SESSION_SCRAPER_URL,
    SUNROOM_DOOR_SYNC_TIMEOUT_SECONDS=SUNROOM_DOOR_SYNC_TIMEOUT_SECONDS,
    api_filter=lambda *args, **kwargs: api_filter(*args, **kwargs),
    api_filter_int=lambda *args, **kwargs: api_filter_int(*args, **kwargs),
    api_filter_options=lambda *args, **kwargs: api_filter_options(*args, **kwargs),
    api_filter_value=lambda *args, **kwargs: api_filter_value(*args, **kwargs),
    api_pick=lambda *args, **kwargs: api_pick(*args, **kwargs),
    async_session=async_session,
    axis_snapshot_day_cache=axis_snapshot_day_cache,
    cleanup_sunroom_door_verifications=lambda *args, **kwargs: cleanup_sunroom_door_verifications(*args, **kwargs),
    get_sun2_summaries=lambda *args, **kwargs: get_sun2_summaries(*args, **kwargs),
    import_job_age=lambda *args, **kwargs: import_job_age(*args, **kwargs),
    logger=logger,
    parse_day=lambda *args, **kwargs: parse_day(*args, **kwargs),
    process_locks=process_locks,
    sunroom_door_period_key=lambda *args, **kwargs: sunroom_door_period_key(*args, **kwargs),
    sunroom_door_verifications=sunroom_door_verifications,
    sunroom_force_sync_candidates=lambda *args, **kwargs: sunroom_force_sync_candidates(*args, **kwargs),
    sunroom_sync_candidate_is_due=lambda *args, **kwargs: sunroom_sync_candidate_is_due(*args, **kwargs),
)
sun_service = sun_services.create_service(sun_dependencies)
api_sun2_bed_row = sun_service["api_sun2_bed_row"]
api_sun2_day_timeline = sun_service["api_sun2_day_timeline"]
api_sun2_forecast_rows = sun_service["api_sun2_forecast_rows"]
api_sun2_member_row = sun_service["api_sun2_member_row"]
api_sun2_overview_tables = sun_service["api_sun2_overview_tables"]
api_sun2_product_sale_row = sun_service["api_sun2_product_sale_row"]
api_sun2_session_row = sun_service["api_sun2_session_row"]
api_sun2_summary_row = sun_service["api_sun2_summary_row"]
api_sun2_weekly_chart = sun_service["api_sun2_weekly_chart"]
axis_snapshot_archive_days = sun_service["axis_snapshot_archive_days"]
axis_snapshot_browser_payload = sun_service["axis_snapshot_browser_payload"]
axis_snapshot_candidates = sun_service["axis_snapshot_candidates"]
axis_snapshot_day_candidates = sun_service["axis_snapshot_day_candidates"]
axis_snapshot_id = sun_service["axis_snapshot_id"]
axis_snapshot_path_for_id = sun_service["axis_snapshot_path_for_id"]
axis_snapshot_series_around = sun_service["axis_snapshot_series_around"]
backfill_sun2_room_identity = sun_service["backfill_sun2_room_identity"]
build_sun2_forecast = sun_service["build_sun2_forecast"]
closest_axis_snapshot_index = sun_service["closest_axis_snapshot_index"]
fetch_sun2_scraper_runtime = sun_service["fetch_sun2_scraper_runtime"]
force_sun2_sync_for_closed_rooms = sun_service["force_sun2_sync_for_closed_rooms"]
get_sun2_axis_snapshot_link_lock = sun_service["get_sun2_axis_snapshot_link_lock"]
get_sun2_session_database_total = sun_service["get_sun2_session_database_total"]
get_sun2_session_options = sun_service["get_sun2_session_options"]
ingest_sun2_beds = sun_service["ingest_sun2_beds"]
ingest_sun2_finance_settlements = sun_service["ingest_sun2_finance_settlements"]
ingest_sun2_members = sun_service["ingest_sun2_members"]
ingest_sun2_product_sales = sun_service["ingest_sun2_product_sales"]
ingest_sun2_room_stats = sun_service["ingest_sun2_room_stats"]
ingest_sun2_tanning_sessions = sun_service["ingest_sun2_tanning_sessions"]
link_axis_snapshots_to_sun2_sessions = sun_service["link_axis_snapshots_to_sun2_sessions"]
nearest_axis_snapshot = sun_service["nearest_axis_snapshot"]
parse_axis_snapshot_id = sun_service["parse_axis_snapshot_id"]
parse_axis_snapshot_time = sun_service["parse_axis_snapshot_time"]
primary_sun2_session_image = sun_service["primary_sun2_session_image"]
replace_sun2_session_image_with_axis_snapshot = sun_service["replace_sun2_session_image_with_axis_snapshot"]
request_sun2_today_sync = sun_service["request_sun2_today_sync"]
run_sun2_axis_snapshot_link_once = sun_service["run_sun2_axis_snapshot_link_once"]
schedule_sun2_axis_snapshot_link = sun_service["schedule_sun2_axis_snapshot_link"]
set_sun2_session_primary_image = sun_service["set_sun2_session_primary_image"]
sun2_axis_snapshot_link_worker = sun_service["sun2_axis_snapshot_link_worker"]
sun2_duplicate_session_id_payload = sun_service["sun2_duplicate_session_id_payload"]
sun2_product_module_payload = sun_service["sun2_product_module_payload"]
sun2_product_sales_month_rows = sun_service["sun2_product_sales_month_rows"]
sun2_product_sales_range_summary = sun_service["sun2_product_sales_range_summary"]
sun2_product_summary_row = sun_service["sun2_product_summary_row"]
sun2_session_axis_start_at = sun_service["sun2_session_axis_start_at"]
sun2_session_axis_target_at = sun_service["sun2_session_axis_target_at"]
sun2_session_axis_target_series = sun_service["sun2_session_axis_target_series"]
sun2_session_image_meta_options = sun_service["sun2_session_image_meta_options"]
sun2_session_image_payload = sun_service["sun2_session_image_payload"]
sun2_sessions_active_minutes_since = sun_service["sun2_sessions_active_minutes_since"]
sun2_sessions_module_payload = sun_service["sun2_sessions_module_payload"]
from fibaro_core.services.runtime import energy as energy_services
energy_dependencies = energy_services.Dependencies(
    ENERGY_ACCUMULATED_ID_BY_POWER_ID=ENERGY_ACCUMULATED_ID_BY_POWER_ID,
    ENERGY_ACCUMULATED_KEYS=ENERGY_ACCUMULATED_KEYS,
    ENERGY_AGGREGATE_GROUP_BY_POWER_ID=ENERGY_AGGREGATE_GROUP_BY_POWER_ID,
    ENERGY_AGGREGATE_HC3_MEMBERS=ENERGY_AGGREGATE_HC3_MEMBERS,
    ENERGY_AGGREGATE_METERS=ENERGY_AGGREGATE_METERS,
    ENERGY_AGGREGATE_METERS_BY_KEY=ENERGY_AGGREGATE_METERS_BY_KEY,
    ENERGY_CIRCUIT_SEED_ROWS=ENERGY_CIRCUIT_SEED_ROWS,
    ENERGY_CIRCUIT_SEED_SOURCE=ENERGY_CIRCUIT_SEED_SOURCE,
    ENERGY_FIBARO_AREAS=ENERGY_FIBARO_AREAS,
    ENERGY_HC3_HOURLY_DISPLAY_OFFSET=ENERGY_HC3_HOURLY_DISPLAY_OFFSET,
    ENERGY_HOURLY_COMPARE_FIELDS=ENERGY_HOURLY_COMPARE_FIELDS,
    ENERGY_LOAD_POWER_PROFILES=ENERGY_LOAD_POWER_PROFILES,
    ENERGY_NODE_TYPES=ENERGY_NODE_TYPES,
    ENERGY_REALTIME_MAX_DELTA_SECONDS=ENERGY_REALTIME_MAX_DELTA_SECONDS,
    ENERGY_SUB_KEYS=ENERGY_SUB_KEYS,
    HC3_ENERGY_LIVE_TIMEOUT_SECONDS=HC3_ENERGY_LIVE_TIMEOUT_SECONDS,
    ROOF_EXHAUST_UNMETERED_W=ROOF_EXHAUST_UNMETERED_W,
    SUMMARY_CACHE=SUMMARY_CACHE,
    SUNBED_ANALYSIS_VENTILATION_MATCH_SECONDS=SUNBED_ANALYSIS_VENTILATION_MATCH_SECONDS,
    SUNBED_POWER_ANALYSIS_CACHE_TTL=SUNBED_POWER_ANALYSIS_CACHE_TTL,
    api_config_value_rows=lambda *args, **kwargs: api_config_value_rows(*args, **kwargs),
    api_day_navigation=lambda *args, **kwargs: api_day_navigation(*args, **kwargs),
    api_import_job_status=lambda *args, **kwargs: api_import_job_status(*args, **kwargs),
    api_pick=lambda *args, **kwargs: api_pick(*args, **kwargs),
    async_session=async_session,
    get_energy_summaries=lambda *args, **kwargs: get_energy_summaries(*args, **kwargs),
    hc3_api_is_configured=lambda *args, **kwargs: hc3_api_is_configured(*args, **kwargs),
    hc3_cached_device_request=lambda *args, **kwargs: hc3_cached_device_request(*args, **kwargs),
    hc3_first_present=lambda *args, **kwargs: hc3_first_present(*args, **kwargs),
    logger=logger,
    nested_extra_value=lambda *args, **kwargs: nested_extra_value(*args, **kwargs),
    parse_boolish=lambda *args, **kwargs: parse_boolish(*args, **kwargs),
    parse_day=lambda *args, **kwargs: parse_day(*args, **kwargs),
)
energy_service = energy_services.create_service(energy_dependencies)
_legacy_energy_circuit_loads_payload = energy_service["_legacy_energy_circuit_loads_payload"]
_meter_based_energy_circuit_loads_payload = energy_service["_meter_based_energy_circuit_loads_payload"]
accumulated_delta = energy_service["accumulated_delta"]
api_energy_circuit_edit = energy_service["api_energy_circuit_edit"]
api_energy_elvia_payload = energy_service["api_energy_elvia_payload"]
api_energy_load_edit = energy_service["api_energy_load_edit"]
api_energy_summary_item = energy_service["api_energy_summary_item"]
api_revenue_accumulated_year_chart = energy_service["api_revenue_accumulated_year_chart"]
build_energy_circuit_loads_payload = energy_service["build_energy_circuit_loads_payload"]
build_sunbed_power_analysis = energy_service["build_sunbed_power_analysis"]
calculated_difference = energy_service["calculated_difference"]
circuit_row_api = energy_service["circuit_row_api"]
clean_energy_load_values = energy_service["clean_energy_load_values"]
clean_energy_node_values = energy_service["clean_energy_node_values"]
cumulative_energy_points = energy_service["cumulative_energy_points"]
cumulative_energy_series = energy_service["cumulative_energy_series"]
default_energy_node_name = energy_service["default_energy_node_name"]
energy_area_cards = energy_service["energy_area_cards"]
energy_elvia_control_module_payload = energy_service["energy_elvia_control_module_payload"]
energy_elvia_module_payload = energy_service["energy_elvia_module_payload"]
energy_fibaro_sample_payload = energy_service["energy_fibaro_sample_payload"]
energy_hour_has_changed = energy_service["energy_hour_has_changed"]
energy_load_hierarchy_item = energy_service["energy_load_hierarchy_item"]
energy_node_branch_ids = energy_service["energy_node_branch_ids"]
energy_node_from_values = energy_service["energy_node_from_values"]
energy_sample_bucket = energy_service["energy_sample_bucket"]
ensure_energy_node_backfill = energy_service["ensure_energy_node_backfill"]
find_or_create_energy_node_for_load = energy_service["find_or_create_energy_node_for_load"]
hc3_energy_device_summary = energy_service["hc3_energy_device_summary"]
hc3_energy_nodes_live = energy_service["hc3_energy_nodes_live"]
ingest_elvia_hours = energy_service["ingest_elvia_hours"]
latest_energy_reconciliation_check = energy_service["latest_energy_reconciliation_check"]
load_row_api = energy_service["load_row_api"]
load_sunbed_power_analysis = energy_service["load_sunbed_power_analysis"]
manual_energy_quickapp_report = energy_service["manual_energy_quickapp_report"]
payload_weather_symbol = energy_service["payload_weather_symbol"]
payload_weather_text = energy_service["payload_weather_text"]
percentile = energy_service["percentile"]
realtime_power_delta_kwh = energy_service["realtime_power_delta_kwh"]
seed_energy_circuits = energy_service["seed_energy_circuits"]
sum_optional = energy_service["sum_optional"]
sunbed_analysis_date_range = energy_service["sunbed_analysis_date_range"]
sunbed_power_cache_warm_worker = energy_service["sunbed_power_cache_warm_worker"]
sunbed_session_bounds = energy_service["sunbed_session_bounds"]
upsert_energy_fibaro_sample = energy_service["upsert_energy_fibaro_sample"]
validate_energy_load_power_values = energy_service["validate_energy_load_power_values"]
validate_energy_node_hc3_values = energy_service["validate_energy_node_hc3_values"]
validate_energy_node_link_uniqueness = energy_service["validate_energy_node_link_uniqueness"]
validate_energy_node_parent = energy_service["validate_energy_node_parent"]
validate_energy_node_profile_values = energy_service["validate_energy_node_profile_values"]
from fibaro_core.services.runtime import parking as parking_services
parking_dependencies = parking_services.Dependencies(
    CAR_INFO_APP_TOKEN=CAR_INFO_APP_TOKEN,
    CAR_INFO_AUTO_TRIGGER_ENABLED=CAR_INFO_AUTO_TRIGGER_ENABLED,
    CAR_INFO_AUTO_TRIGGER_MAX_PER_SVV_RUN=CAR_INFO_AUTO_TRIGGER_MAX_PER_SVV_RUN,
    CAR_INFO_CANDIDATE_RETRY_HOURS=CAR_INFO_CANDIDATE_RETRY_HOURS,
    CAR_INFO_CANDIDATE_TRANSIENT_RETRY_MINUTES=CAR_INFO_CANDIDATE_TRANSIENT_RETRY_MINUTES,
    CAR_INFO_LOOKUP_TIMEOUT_SECONDS=CAR_INFO_LOOKUP_TIMEOUT_SECONDS,
    CAR_INFO_LOOKUP_URL=CAR_INFO_LOOKUP_URL,
    EASYPARK_DOWNLOADER_URL=EASYPARK_DOWNLOADER_URL,
    EASYPARK_REQUIRED_COLUMNS=EASYPARK_REQUIRED_COLUMNS,
    PARKING_OCCUPANCY_SCALE_MAX=PARKING_OCCUPANCY_SCALE_MAX,
    PARKING_TIMELINE_CAPACITY=PARKING_TIMELINE_CAPACITY,
    PARKING_TIMELINE_ROWS=PARKING_TIMELINE_ROWS,
    PARKING_TIME_PERIOD_OPTIONS=PARKING_TIME_PERIOD_OPTIONS,
    PARKING_TIME_WEEKDAYS=PARKING_TIME_WEEKDAYS,
    PARKING_WEEKLY_AVERAGE_PERIOD_OPTIONS=PARKING_WEEKLY_AVERAGE_PERIOD_OPTIONS,
    SUMMARY_CACHE=SUMMARY_CACHE,
    SVV_API_AUTH_HEADER=SVV_API_AUTH_HEADER,
    SVV_API_AUTH_PREFIX=SVV_API_AUTH_PREFIX,
    SVV_API_KEY=SVV_API_KEY,
    SVV_API_URL=SVV_API_URL,
    SVV_PERMANENT_NO_DATA_STATUSES=SVV_PERMANENT_NO_DATA_STATUSES,
    SVV_RETRY_AFTER_HOURS=SVV_RETRY_AFTER_HOURS,
    SVV_SYNC_BATCH_SIZE=SVV_SYNC_BATCH_SIZE,
    SVV_SYNC_INTERVAL_MINUTES=SVV_SYNC_INTERVAL_MINUTES,
    SVV_TRANSIENT_RETRY_AFTER_MINUTES=SVV_TRANSIENT_RETRY_AFTER_MINUTES,
    SVV_TRANSIENT_STATUSES=SVV_TRANSIENT_STATUSES,
    api_filter_value=lambda *args, **kwargs: api_filter_value(*args, **kwargs),
    async_session=async_session,
    clear_summary_cache=lambda *args, **kwargs: clear_summary_cache(*args, **kwargs),
    exact_search_text=lambda *args, **kwargs: exact_search_text(*args, **kwargs),
    exact_word_match=lambda *args, **kwargs: exact_word_match(*args, **kwargs),
    get_parking_summaries=lambda *args, **kwargs: get_parking_summaries(*args, **kwargs),
    is_not_found_marker=lambda *args, **kwargs: is_not_found_marker(*args, **kwargs),
    parse_day=lambda *args, **kwargs: parse_day(*args, **kwargs),
    parse_optional_date=lambda *args, **kwargs: parse_optional_date(*args, **kwargs),
    record_import_job=lambda *args, **kwargs: record_import_job(*args, **kwargs),
    require_settings_access=lambda *args, **kwargs: require_settings_access(*args, **kwargs),
)
parking_service = parking_services.create_service(parking_dependencies)
api_parking_clear_area_not_found_action = parking_service["api_parking_clear_area_not_found_action"]
api_parking_day_timeline = parking_service["api_parking_day_timeline"]
api_parking_default_actions = parking_service["api_parking_default_actions"]
api_parking_forecast_evolution_chart = parking_service["api_parking_forecast_evolution_chart"]
api_parking_forecast_rows = parking_service["api_parking_forecast_rows"]
api_parking_overview_tables = parking_service["api_parking_overview_tables"]
api_parking_saved_forecast_rows = parking_service["api_parking_saved_forecast_rows"]
api_parking_summary_row = parking_service["api_parking_summary_row"]
api_parking_time_distribution = parking_service["api_parking_time_distribution"]
api_parking_weekly_chart = parking_service["api_parking_weekly_chart"]
build_parking_forecast = parking_service["build_parking_forecast"]
car_info_lookup_request = parking_service["car_info_lookup_request"]
clean_easypark_value = parking_service["clean_easypark_value"]
clear_parking_vehicle_not_found_area = parking_service["clear_parking_vehicle_not_found_area"]
clear_parking_vehicle_not_found_fields = parking_service["clear_parking_vehicle_not_found_fields"]
decode_easypark_csv = parking_service["decode_easypark_csv"]
easypark_downloader_request = parking_service["easypark_downloader_request"]
easypark_downloader_status = parking_service["easypark_downloader_status"]
easypark_float = parking_service["easypark_float"]
easypark_int = parking_service["easypark_int"]
easypark_minutes = parking_service["easypark_minutes"]
easypark_next_run_at_from_status = parking_service["easypark_next_run_at_from_status"]
easypark_recent_period = parking_service["easypark_recent_period"]
easypark_timestamp = parking_service["easypark_timestamp"]
fallback_car_info_import_status = parking_service["fallback_car_info_import_status"]
has_car_info_app_access = parking_service["has_car_info_app_access"]
ingest_easypark_csv = parking_service["ingest_easypark_csv"]
is_car_info_app_request_path = parking_service["is_car_info_app_request_path"]
parking_area_missing_rows_for_period = parking_service["parking_area_missing_rows_for_period"]
parking_area_overview_data = parking_service["parking_area_overview_data"]
parking_area_period = parking_service["parking_area_period"]
parking_area_period_conditions = parking_service["parking_area_period_conditions"]
parking_area_row_api = parking_service["parking_area_row_api"]
parking_calendar_comparison_week = parking_service["parking_calendar_comparison_week"]
parking_calendar_comparison_week_ranges = parking_service["parking_calendar_comparison_week_ranges"]
parking_car_info_candidate_rows = parking_service["parking_car_info_candidate_rows"]
parking_departure_slot_delta_minutes = parking_service["parking_departure_slot_delta_minutes"]
parking_missing_area_rows = parking_service["parking_missing_area_rows"]
parking_missing_name_rows = parking_service["parking_missing_name_rows"]
parking_period_summary = parking_service["parking_period_summary"]
parking_previous_stats_for_rows = parking_service["parking_previous_stats_for_rows"]
parking_row_api = parking_service["parking_row_api"]
parking_time_distribution_period = parking_service["parking_time_distribution_period"]
parking_time_weekday_day_counts = parking_service["parking_time_weekday_day_counts"]
parking_timeline_end = parking_service["parking_timeline_end"]
parking_valid_vehicle_area_condition = parking_service["parking_valid_vehicle_area_condition"]
parking_vehicle_by_plate_or_compact = parking_service["parking_vehicle_by_plate_or_compact"]
parking_vehicle_count_stats = parking_service["parking_vehicle_count_stats"]
parking_vehicle_lookup_payload = parking_service["parking_vehicle_lookup_payload"]
parking_vehicle_not_found_field_labels = parking_service["parking_vehicle_not_found_field_labels"]
parking_vehicle_row_api = parking_service["parking_vehicle_row_api"]
parking_vehicle_search_condition = parking_service["parking_vehicle_search_condition"]
parking_vehicle_svv_worker = parking_service["parking_vehicle_svv_worker"]
parking_weekly_average_payload = parking_service["parking_weekly_average_payload"]
parking_weekly_average_period = parking_service["parking_weekly_average_period"]
parking_weekly_selected_years = parking_service["parking_weekly_selected_years"]
parking_weekly_year_comparison_payload = parking_service["parking_weekly_year_comparison_payload"]
parse_easypark_csv = parking_service["parse_easypark_csv"]
refresh_parking_vehicle_summary = parking_service["refresh_parking_vehicle_summary"]
require_settings_or_car_info_access = parking_service["require_settings_or_car_info_access"]
run_vehicle_svv_sync = parking_service["run_vehicle_svv_sync"]
save_parking_forecast_after_import = parking_service["save_parking_forecast_after_import"]
status_parking_timeline_event = parking_service["status_parking_timeline_event"]
svv_api_lookup_sync = parking_service["svv_api_lookup_sync"]
svv_candidate_plates = parking_service["svv_candidate_plates"]
trigger_car_info_after_svv_no_data = parking_service["trigger_car_info_after_svv_no_data"]
unpaid_registered_vehicle_stays_payload = parking_service["unpaid_registered_vehicle_stays_payload"]
upsert_vehicle_svv_data = parking_service["upsert_vehicle_svv_data"]
vehicle_area_not_found_condition = parking_service["vehicle_area_not_found_condition"]
vehicle_blank_area_condition = parking_service["vehicle_blank_area_condition"]
vehicle_blank_name_condition = parking_service["vehicle_blank_name_condition"]
vehicle_car_info_candidate_condition = parking_service["vehicle_car_info_candidate_condition"]
vehicle_car_info_country_condition = parking_service["vehicle_car_info_country_condition"]
vehicle_car_info_due_condition = parking_service["vehicle_car_info_due_condition"]
vehicle_missing_area_condition = parking_service["vehicle_missing_area_condition"]
vehicle_missing_name_condition = parking_service["vehicle_missing_name_condition"]
vehicle_name_not_found_condition = parking_service["vehicle_name_not_found_condition"]
from fibaro_core.services.runtime import building as building_services
building_dependencies = building_services.Dependencies(
    CONFIG_DEFINITIONS=CONFIG_DEFINITIONS,
    CONTROL_DEVICES=CONTROL_DEVICES,
    HC3_BASE_URL=HC3_BASE_URL,
    HC3_DOOR_POLL_TIMEOUT_SECONDS=HC3_DOOR_POLL_TIMEOUT_SECONDS,
    HC3_DOOR_UNEXPECTED_RECHECK_MINUTES=HC3_DOOR_UNEXPECTED_RECHECK_MINUTES,
    HC3_ENERGY_DEVICE_LIST_CACHE_SECONDS=HC3_ENERGY_DEVICE_LIST_CACHE_SECONDS,
    HC3_ENERGY_LIVE_TIMEOUT_SECONDS=HC3_ENERGY_LIVE_TIMEOUT_SECONDS,
    HC3_PASS=HC3_PASS,
    HC3_SWITCH_POLL_TIMEOUT_SECONDS=HC3_SWITCH_POLL_TIMEOUT_SECONDS,
    HC3_SWITCH_STATUS_CACHE_SECONDS=HC3_SWITCH_STATUS_CACHE_SECONDS,
    HC3_USER=HC3_USER,
    LIGHT_TIMELINE_DEVICES=LIGHT_TIMELINE_DEVICES,
    MET_LAT=MET_LAT,
    MET_LON=MET_LON,
    NTFY_LIGHTS_TOPIC=NTFY_LIGHTS_TOPIC,
    NTFY_VENTILATION_TOPIC=NTFY_VENTILATION_TOPIC,
    VENT_TIMELINE_DEVICES=VENT_TIMELINE_DEVICES,
    add_segment=lambda *args, **kwargs: add_segment(*args, **kwargs),
    api_bool_state=lambda *args, **kwargs: api_bool_state(*args, **kwargs),
    async_session=async_session,
    clean_display_text=lambda *args, **kwargs: clean_display_text(*args, **kwargs),
    display_action=lambda *args, **kwargs: display_action(*args, **kwargs),
    display_segments=lambda *args, **kwargs: display_segments(*args, **kwargs),
    enqueue_ntfy_message=lambda *args, **kwargs: enqueue_ntfy_message(*args, **kwargs),
    hc3_door_unexpected_verified_until=hc3_door_unexpected_verified_until,
    hc3_energy_device_list_cache=hc3_energy_device_list_cache,
    hc3_switch_status_cache=hc3_switch_status_cache,
    logger=logger,
    parse_boolish=lambda *args, **kwargs: parse_boolish(*args, **kwargs),
    payload_weather_symbol=lambda *args, **kwargs: payload_weather_symbol(*args, **kwargs),
    payload_weather_text=lambda *args, **kwargs: payload_weather_text(*args, **kwargs),
    percent_between=lambda *args, **kwargs: percent_between(*args, **kwargs),
    row_to_dict=lambda *args, **kwargs: row_to_dict(*args, **kwargs),
    status_parking_timeline_event=lambda *args, **kwargs: status_parking_timeline_event(*args, **kwargs),
    sunbed_session_bounds=lambda *args, **kwargs: sunbed_session_bounds(*args, **kwargs),
    time_minutes=lambda *args, **kwargs: time_minutes(*args, **kwargs),
    total_from_segments=lambda *args, **kwargs: total_from_segments(*args, **kwargs),
    value_from_payload=lambda *args, **kwargs: value_from_payload(*args, **kwargs),
    weather_label=lambda *args, **kwargs: weather_label(*args, **kwargs),
)
building_service = building_services.create_service(building_dependencies)
alarm_event_payload = building_service["alarm_event_payload"]
api_config_field_rows = building_service["api_config_field_rows"]
api_config_history_rows = building_service["api_config_history_rows"]
api_config_value_rows = building_service["api_config_value_rows"]
attach_hc3_alarm_verification = building_service["attach_hc3_alarm_verification"]
build_light_chart_markers = building_service["build_light_chart_markers"]
build_light_timeline_group = building_service["build_light_timeline_group"]
build_lux_day = building_service["build_lux_day"]
build_lux_sparkline = building_service["build_lux_sparkline"]
build_solar_elevation_samples = building_service["build_solar_elevation_samples"]
build_temp_day = building_service["build_temp_day"]
build_timeline_group = building_service["build_timeline_group"]
build_timeline_item = building_service["build_timeline_item"]
config_context = building_service["config_context"]
config_defaults = building_service["config_defaults"]
config_definition = building_service["config_definition"]
config_devices = building_service["config_devices"]
config_operational_notes = building_service["config_operational_notes"]
config_payload = building_service["config_payload"]
config_rules = building_service["config_rules"]
config_stat_cards = building_service["config_stat_cards"]
config_summary_rows = building_service["config_summary_rows"]
config_values_from_form = building_service["config_values_from_form"]
config_values_from_payload = building_service["config_values_from_payload"]
control_settings_payload = building_service["control_settings_payload"]
dedupe_samples_by_bucket = building_service["dedupe_samples_by_bucket"]
empty_ventilation_day_payload = building_service["empty_ventilation_day_payload"]
event_detail = building_service["event_detail"]
event_device_key = building_service["event_device_key"]
event_extra_key = building_service["event_extra_key"]
event_matches_device = building_service["event_matches_device"]
fetch_lux_samples = building_service["fetch_lux_samples"]
generic_from_payload = building_service["generic_from_payload"]
get_or_create_config = building_service["get_or_create_config"]
hc3_api_is_configured = building_service["hc3_api_is_configured"]
hc3_basic_auth_header = building_service["hc3_basic_auth_header"]
hc3_cached_device_request = building_service["hc3_cached_device_request"]
hc3_control_device_id = building_service["hc3_control_device_id"]
hc3_device_request = building_service["hc3_device_request"]
hc3_devices_request = building_service["hc3_devices_request"]
hc3_fetch_switch_status = building_service["hc3_fetch_switch_status"]
hc3_fetch_switch_statuses = building_service["hc3_fetch_switch_statuses"]
hc3_first_present = building_service["hc3_first_present"]
hc3_switch_config_for_timeline_device = building_service["hc3_switch_config_for_timeline_device"]
hc3_switch_status_from_device = building_service["hc3_switch_status_from_device"]
hc3_unexpected_poll_cooldown_active = building_service["hc3_unexpected_poll_cooldown_active"]
light_from_payload = building_service["light_from_payload"]
light_ntfy_payload = building_service["light_ntfy_payload"]
light_rules = building_service["light_rules"]
light_sample_from_payload = building_service["light_sample_from_payload"]
light_sample_state = building_service["light_sample_state"]
light_status_text = building_service["light_status_text"]
lux_scale = building_service["lux_scale"]
lux_tick_label = building_service["lux_tick_label"]
lux_tick_values = building_service["lux_tick_values"]
lux_y = building_service["lux_y"]
mark_hc3_unexpected_poll_verified = building_service["mark_hc3_unexpected_poll_verified"]
merge_config_values = building_service["merge_config_values"]
merged_extra = building_service["merged_extra"]
parse_config_value = building_service["parse_config_value"]
point_from_row = building_service["point_from_row"]
publish_light_ntfy = building_service["publish_light_ntfy"]
publish_ventilation_ntfy = building_service["publish_ventilation_ntfy"]
sample_state = building_service["sample_state"]
state_from_event = building_service["state_from_event"]
status_sun_timeline_event = building_service["status_sun_timeline_event"]
status_timeline_lane = building_service["status_timeline_lane"]
temp_axis = building_service["temp_axis"]
temp_label = building_service["temp_label"]
temp_y = building_service["temp_y"]
upsert_kjeller_measurement_sample = building_service["upsert_kjeller_measurement_sample"]
validate_config_values = building_service["validate_config_values"]
vent_from_payload = building_service["vent_from_payload"]
vent_sample_from_payload = building_service["vent_sample_from_payload"]
ventilation_day_payload = building_service["ventilation_day_payload"]
ventilation_latest_payload = building_service["ventilation_latest_payload"]
ventilation_ntfy_payload = building_service["ventilation_ntfy_payload"]
ventilation_rules = building_service["ventilation_rules"]
ventilation_settings_payload = building_service["ventilation_settings_payload"]
ventilation_status_payload = building_service["ventilation_status_payload"]
from fibaro_core.services.runtime import cleaning as cleaning_services
cleaning_dependencies = cleaning_services.Dependencies(
    DREAME_CONTROL_TOKEN=DREAME_CONTROL_TOKEN,
    DREAME_LOGGER_URL=DREAME_LOGGER_URL,
    ROBOROCK_CONTROL_TOKEN=ROBOROCK_CONTROL_TOKEN,
    ROBOROCK_DOOR_AUTOMATION_POLL_SECONDS=ROBOROCK_DOOR_AUTOMATION_POLL_SECONDS,
    ROBOROCK_LOGGER_URL=ROBOROCK_LOGGER_URL,
    _roborock_door_automation_lock=_roborock_door_automation_lock,
    async_session=async_session,
    config_defaults=lambda *args, **kwargs: config_defaults(*args, **kwargs),
    door_change_rows=lambda *args, **kwargs: door_change_rows(*args, **kwargs),
    door_event_state_bool=lambda *args, **kwargs: door_event_state_bool(*args, **kwargs),
    logger=logger,
    merge_config_values=lambda *args, **kwargs: merge_config_values(*args, **kwargs),
    row_to_dict=lambda *args, **kwargs: row_to_dict(*args, **kwargs),
)
cleaning_service = cleaning_services.create_service(cleaning_dependencies)
api_roborock_active_cycle = cleaning_service["api_roborock_active_cycle"]
apply_roborock_cleaning_profile_values = cleaning_service["apply_roborock_cleaning_profile_values"]
ensure_default_roborock_cleaning_profiles = cleaning_service["ensure_default_roborock_cleaning_profiles"]
ensure_default_roborock_door_automation = cleaning_service["ensure_default_roborock_door_automation"]
ensure_roborock_schedule_snapshot_backfill = cleaning_service["ensure_roborock_schedule_snapshot_backfill"]
import_roborock_cleaning_zones = cleaning_service["import_roborock_cleaning_zones"]
ingest_roborock_robot = cleaning_service["ingest_roborock_robot"]
ingest_roborock_telemetry_robot = cleaning_service["ingest_roborock_telemetry_robot"]
latest_cleaning_robot_sample = cleaning_service["latest_cleaning_robot_sample"]
post_dreame_control = cleaning_service["post_dreame_control"]
post_roborock_control = cleaning_service["post_roborock_control"]
record_roborock_schedule_snapshot = cleaning_service["record_roborock_schedule_snapshot"]
roborock_cleaning_profile_payload = cleaning_service["roborock_cleaning_profile_payload"]
roborock_door_automation_payload = cleaning_service["roborock_door_automation_payload"]
roborock_door_automation_worker = cleaning_service["roborock_door_automation_worker"]
roborock_schedule_params = cleaning_service["roborock_schedule_params"]
roborock_schedule_snapshot_fingerprint = cleaning_service["roborock_schedule_snapshot_fingerprint"]
roborock_schedule_snapshot_rows = cleaning_service["roborock_schedule_snapshot_rows"]
roborock_telemetry_sample_values = cleaning_service["roborock_telemetry_sample_values"]
roborock_water_interlock_from_sample = cleaning_service["roborock_water_interlock_from_sample"]
run_roborock_door_automation_once = cleaning_service["run_roborock_door_automation_once"]
from fibaro_core.services.runtime import sunroom as sunroom_services
sunroom_dependencies = sunroom_services.Dependencies(
    ALARM_APP_URL=ALARM_APP_URL,
    DOOR_SENSOR_CONFIG=DOOR_SENSOR_CONFIG,
    DOOR_SENSOR_IDS=DOOR_SENSOR_IDS,
    HC3_DOOR_DEBOUNCE_SECONDS=HC3_DOOR_DEBOUNCE_SECONDS,
    HC3_DOOR_OTHER_OPEN_VERIFY_MINUTES=HC3_DOOR_OTHER_OPEN_VERIFY_MINUTES,
    HC3_DOOR_SOLROOM_CLOSED_VERIFY_MINUTES=HC3_DOOR_SOLROOM_CLOSED_VERIFY_MINUTES,
    HC3_DOOR_UNEXPECTED_CHECK_INITIAL_DELAY_SECONDS=HC3_DOOR_UNEXPECTED_CHECK_INITIAL_DELAY_SECONDS,
    HC3_DOOR_UNEXPECTED_CHECK_INTERVAL_SECONDS=HC3_DOOR_UNEXPECTED_CHECK_INTERVAL_SECONDS,
    NTFY_DOORS_TOPIC=NTFY_DOORS_TOPIC,
    SUNROOM_DOOR_ALERT_AFTER_END_MINUTES=SUNROOM_DOOR_ALERT_AFTER_END_MINUTES,
    SUNROOM_DOOR_CRITICAL_MINUTES=SUNROOM_DOOR_CRITICAL_MINUTES,
    SUNROOM_DOOR_EXIT_GRACE_MINUTES=SUNROOM_DOOR_EXIT_GRACE_MINUTES,
    SUNROOM_DOOR_FAN_AFTER_RUN_MINUTES=SUNROOM_DOOR_FAN_AFTER_RUN_MINUTES,
    SUNROOM_DOOR_FORCED_SYNC_MINUTES=SUNROOM_DOOR_FORCED_SYNC_MINUTES,
    SUNROOM_DOOR_MONITOR_INITIAL_DELAY_SECONDS=SUNROOM_DOOR_MONITOR_INITIAL_DELAY_SECONDS,
    SUNROOM_DOOR_MONITOR_INTERVAL_SECONDS=SUNROOM_DOOR_MONITOR_INTERVAL_SECONDS,
    SUNROOM_DOOR_NEW_SESSION_GRACE_MINUTES=SUNROOM_DOOR_NEW_SESSION_GRACE_MINUTES,
    SUNROOM_DOOR_NO_SESSION_ALARM_MINUTES=SUNROOM_DOOR_NO_SESSION_ALARM_MINUTES,
    SUNROOM_DOOR_PAYMENT_DELAY_MINUTES=SUNROOM_DOOR_PAYMENT_DELAY_MINUTES,
    SUNROOM_DOOR_SESSION_GRACE_MINUTES=SUNROOM_DOOR_SESSION_GRACE_MINUTES,
    SUNROOM_DOOR_SESSION_LOOKBACK_HOURS=SUNROOM_DOOR_SESSION_LOOKBACK_HOURS,
    SUNROOM_DOOR_SYNC_FAILURE_ALARM_MINUTES=SUNROOM_DOOR_SYNC_FAILURE_ALARM_MINUTES,
    SUNROOM_DOOR_SYNC_MAX_ATTEMPTS=SUNROOM_DOOR_SYNC_MAX_ATTEMPTS,
    SUNROOM_DOOR_SYNC_MIN_INTERVAL_SECONDS=SUNROOM_DOOR_SYNC_MIN_INTERVAL_SECONDS,
    SUNROOM_DOOR_WARN_AFTER_END_MINUTES=SUNROOM_DOOR_WARN_AFTER_END_MINUTES,
    SUNROOM_BED_STATUS_MAX_AGE_MINUTES=SUNROOM_BED_STATUS_MAX_AGE_MINUTES,
    alarm_event_payload=lambda *args, **kwargs: alarm_event_payload(*args, **kwargs),
    async_session=async_session,
    attach_hc3_alarm_verification=lambda *args, **kwargs: attach_hc3_alarm_verification(*args, **kwargs),
    enqueue_ntfy_message=lambda *args, **kwargs: enqueue_ntfy_message(*args, **kwargs),
    fetch_sun2_scraper_runtime=lambda *args, **kwargs: fetch_sun2_scraper_runtime(*args, **kwargs),
    force_sun2_sync_for_closed_rooms=lambda *args, **kwargs: force_sun2_sync_for_closed_rooms(*args, **kwargs),
    hc3_api_is_configured=lambda *args, **kwargs: hc3_api_is_configured(*args, **kwargs),
    hc3_device_request=lambda *args, **kwargs: hc3_device_request(*args, **kwargs),
    hc3_first_present=lambda *args, **kwargs: hc3_first_present(*args, **kwargs),
    hc3_unexpected_poll_cooldown_active=lambda *args, **kwargs: hc3_unexpected_poll_cooldown_active(*args, **kwargs),
    logger=logger,
    mark_hc3_unexpected_poll_verified=lambda *args, **kwargs: mark_hc3_unexpected_poll_verified(*args, **kwargs),
    ntfy_subscribe_url=lambda *args, **kwargs: ntfy_subscribe_url(*args, **kwargs),
    ntfy_topic_url=lambda *args, **kwargs: ntfy_topic_url(*args, **kwargs),
    parse_boolish=lambda *args, **kwargs: parse_boolish(*args, **kwargs),
    parse_day=lambda *args, **kwargs: parse_day(*args, **kwargs),
    record_import_job=lambda *args, **kwargs: record_import_job(*args, **kwargs),
    sunroom_door_verifications=sunroom_door_verifications,
)
sunroom_service = sunroom_services.create_service(sunroom_dependencies)
apply_sunroom_bed_status_to_active_periods = sunroom_service["apply_sunroom_bed_status_to_active_periods"]
apply_sunroom_alarm_verification = sunroom_service["apply_sunroom_alarm_verification"]
cleanup_sunroom_door_verifications = sunroom_service["cleanup_sunroom_door_verifications"]
door_action_from_state = sunroom_service["door_action_from_state"]
door_age_label = sunroom_service["door_age_label"]
door_change_rows = sunroom_service["door_change_rows"]
door_change_text = sunroom_service["door_change_text"]
door_closed_period_payload = sunroom_service["door_closed_period_payload"]
door_closed_periods = sunroom_service["door_closed_periods"]
door_config_device_key = sunroom_service["door_config_device_key"]
door_duration_label = sunroom_service["door_duration_label"]
door_event_device_key = sunroom_service["door_event_device_key"]
door_event_from_payload = sunroom_service["door_event_from_payload"]
door_event_payload = sunroom_service["door_event_payload"]
door_event_state_bool = sunroom_service["door_event_state_bool"]
door_open_periods = sunroom_service["door_open_periods"]
door_period_device_key = sunroom_service["door_period_device_key"]
door_period_payload = sunroom_service["door_period_payload"]
door_poll_sync_payload = sunroom_service["door_poll_sync_payload"]
door_state_age_minutes = sunroom_service["door_state_age_minutes"]
door_state_from_event = sunroom_service["door_state_from_event"]
door_status_payload = sunroom_service["door_status_payload"]
door_title_for_row = sunroom_service["door_title_for_row"]
door_unexpected_reason = sunroom_service["door_unexpected_reason"]
hc3_door_poll_is_configured = sunroom_service["hc3_door_poll_is_configured"]
hc3_door_poll_worker = sunroom_service["hc3_door_poll_worker"]
hc3_door_status_from_device = sunroom_service["hc3_door_status_from_device"]
hc3_door_unexpected_targets = sunroom_service["hc3_door_unexpected_targets"]
hc3_fetch_all_door_statuses = sunroom_service["hc3_fetch_all_door_statuses"]
hc3_fetch_door_status = sunroom_service["hc3_fetch_door_status"]
hc3_fetch_door_statuses = sunroom_service["hc3_fetch_door_statuses"]
latest_door_changes_by_device = sunroom_service["latest_door_changes_by_device"]
latest_door_event_by_device = sunroom_service["latest_door_event_by_device"]
operations_recent_door_items = sunroom_service["operations_recent_door_items"]
publish_door_ntfy = sunroom_service["publish_door_ntfy"]
publish_sunroom_door_alerts = sunroom_service["publish_sunroom_door_alerts"]
run_hc3_door_poll_once = sunroom_service["run_hc3_door_poll_once"]
run_hc3_door_unexpected_check_once = sunroom_service["run_hc3_door_unexpected_check_once"]
sunroom_alarm_detected_at = sunroom_service["sunroom_alarm_detected_at"]
sunroom_alarm_event_key = sunroom_service["sunroom_alarm_event_key"]
sunroom_alarm_message = sunroom_service["sunroom_alarm_message"]
sunroom_alert_key = sunroom_service["sunroom_alert_key"]
sunroom_bed_id_for_config = sunroom_service["sunroom_bed_id_for_config"]
sunroom_best_session_for_door = sunroom_service["sunroom_best_session_for_door"]
sunroom_canonical_room_id = sunroom_service["sunroom_canonical_room_id"]
sunroom_config_for_room_id = sunroom_service["sunroom_config_for_room_id"]
sunroom_day_event = sunroom_service["sunroom_day_event"]
sunroom_display_number = sunroom_service["sunroom_display_number"]
sunroom_door_alarm_payload = sunroom_service["sunroom_door_alarm_payload"]
sunroom_door_event_marker = sunroom_service["sunroom_door_event_marker"]
sunroom_door_monitor_worker = sunroom_service["sunroom_door_monitor_worker"]
sunroom_door_period_key = sunroom_service["sunroom_door_period_key"]
sunroom_door_session_payload = sunroom_service["sunroom_door_session_payload"]
sunroom_duration_label = sunroom_service["sunroom_duration_label"]
sunroom_energy_sample_items = sunroom_service["sunroom_energy_sample_items"]
sunroom_energy_sample_window = sunroom_service["sunroom_energy_sample_window"]
sunroom_entrance_config = sunroom_service["sunroom_entrance_config"]
sunroom_entrance_markers = sunroom_service["sunroom_entrance_markers"]
sunroom_expected_exit_at = sunroom_service["sunroom_expected_exit_at"]
sunroom_force_sync_candidates = sunroom_service["sunroom_force_sync_candidates"]
sunroom_identity_for_config = sunroom_service["sunroom_identity_for_config"]
sunroom_item_may_have_new_session = sunroom_service["sunroom_item_may_have_new_session"]
sunroom_logic_event = sunroom_service["sunroom_logic_event"]
sunroom_logic_for_room = sunroom_service["sunroom_logic_for_room"]
sunroom_logic_payload = sunroom_service["sunroom_logic_payload"]
sunroom_marker_day_event = sunroom_service["sunroom_marker_day_event"]
sunroom_match_session_for_period = sunroom_service["sunroom_match_session_for_period"]
sunroom_median_float = sunroom_service["sunroom_median_float"]
sunroom_money_label = sunroom_service["sunroom_money_label"]
sunroom_parse_time_value = sunroom_service["sunroom_parse_time_value"]
sunroom_period_day_events = sunroom_service["sunroom_period_day_events"]
sunroom_period_payload = sunroom_service["sunroom_period_payload"]
sunroom_period_status = sunroom_service["sunroom_period_status"]
sunroom_power_marker = sunroom_service["sunroom_power_marker"]
sunroom_power_markers = sunroom_service["sunroom_power_markers"]
sunroom_room_detail_payload = sunroom_service["sunroom_room_detail_payload"]
sunroom_room_id_for_config = sunroom_service["sunroom_room_id_for_config"]
sunroom_room_overview_payload = sunroom_service["sunroom_room_overview_payload"]
sunroom_session_day_events = sunroom_service["sunroom_session_day_events"]
sunroom_session_end_at = sunroom_service["sunroom_session_end_at"]
sunroom_session_energy_evidence = sunroom_service["sunroom_session_energy_evidence"]
sunroom_session_energy_window = sunroom_service["sunroom_session_energy_window"]
sunroom_session_matches_closed_period = sunroom_service["sunroom_session_matches_closed_period"]
sunroom_session_matches_period = sunroom_service["sunroom_session_matches_period"]
sunroom_session_payload = sunroom_service["sunroom_session_payload"]
sunroom_session_period_score = sunroom_service["sunroom_session_period_score"]
sunroom_session_sun_start_at = sunroom_service["sunroom_session_sun_start_at"]
sunroom_status_item = sunroom_service["sunroom_status_item"]
sunroom_bed_status_payload = sunroom_service["sunroom_bed_status_payload"]
sunroom_sync_candidate_is_due = sunroom_service["sunroom_sync_candidate_is_due"]
sunroom_sync_reason_label = sunroom_service["sunroom_sync_reason_label"]
sunroom_watt_label = sunroom_service["sunroom_watt_label"]
sync_sunroom_alarm_history = sunroom_service["sync_sunroom_alarm_history"]
verify_sunroom_alert_doors_with_hc3 = sunroom_service["verify_sunroom_alert_doors_with_hc3"]
from fibaro_core.services.runtime import linking as linking_services
linking_dependencies = linking_services.Dependencies(
    CAR_INFO_APP_TOKEN=CAR_INFO_APP_TOKEN,
    KOBLE_WORKER_TOKEN=KOBLE_WORKER_TOKEN,
    PARKING_SUN_LINK_CONFIRMED=PARKING_SUN_LINK_CONFIRMED,
    PARKING_SUN_LINK_PENDING=PARKING_SUN_LINK_PENDING,
    PARKING_SUN_LINK_REJECTED=PARKING_SUN_LINK_REJECTED,
    PARKING_SUN_LINK_STATUSES=PARKING_SUN_LINK_STATUSES,
    import_job_definition=lambda *args, **kwargs: import_job_definition(*args, **kwargs),
)
linking_service = linking_services.create_service(linking_dependencies)
api_parking_sun_link_candidate_row = linking_service["api_parking_sun_link_candidate_row"]
api_parking_sun_link_match_row = linking_service["api_parking_sun_link_match_row"]
api_parking_sun_link_state_row = linking_service["api_parking_sun_link_state_row"]
get_parking_sun_link_state = linking_service["get_parking_sun_link_state"]
has_koble_worker_access = linking_service["has_koble_worker_access"]
is_koble_worker_request_path = linking_service["is_koble_worker_request_path"]
parking_sun_link_assessment = linking_service["parking_sun_link_assessment"]
parking_sun_link_candidate_edit = linking_service["parking_sun_link_candidate_edit"]
parking_sun_link_candidates = linking_service["parking_sun_link_candidates"]
parking_sun_link_matched_paid_totals = linking_service["parking_sun_link_matched_paid_totals"]
parking_sun_link_probability = linking_service["parking_sun_link_probability"]
parking_sun_link_qualified_distinct_matched_paid_total = linking_service["parking_sun_link_qualified_distinct_matched_paid_total"]
parking_sun_link_settings_edit = linking_service["parking_sun_link_settings_edit"]
parking_sun_link_status_value = linking_service["parking_sun_link_status_value"]
refresh_parking_sun_link_candidate_pairs = linking_service["refresh_parking_sun_link_candidate_pairs"]
refresh_parking_sun_link_state_counts = linking_service["refresh_parking_sun_link_state_counts"]
reset_parking_sun_link_data = linking_service["reset_parking_sun_link_data"]
update_parking_sun_link_import_status = linking_service["update_parking_sun_link_import_status"]
from fibaro_core.services.runtime import presentation as presentation_services
presentation_dependencies = presentation_services.Dependencies(
    DAY_ZOOM_OPTIONS=DAY_ZOOM_OPTIONS,
    api_sun2_bed_row=lambda *args, **kwargs: api_sun2_bed_row(*args, **kwargs),
    api_sun2_day_timeline=lambda *args, **kwargs: api_sun2_day_timeline(*args, **kwargs),
    api_sun2_forecast_rows=lambda *args, **kwargs: api_sun2_forecast_rows(*args, **kwargs),
    api_sun2_member_row=lambda *args, **kwargs: api_sun2_member_row(*args, **kwargs),
    api_sun2_overview_tables=lambda *args, **kwargs: api_sun2_overview_tables(*args, **kwargs),
    api_sun2_session_row=lambda *args, **kwargs: api_sun2_session_row(*args, **kwargs),
    api_sun2_summary_row=lambda *args, **kwargs: api_sun2_summary_row(*args, **kwargs),
    api_sun2_weekly_chart=lambda *args, **kwargs: api_sun2_weekly_chart(*args, **kwargs),
    async_session=async_session,
    build_sun2_forecast=lambda *args, **kwargs: build_sun2_forecast(*args, **kwargs),
    get_sun2_session_database_total=lambda *args, **kwargs: get_sun2_session_database_total(*args, **kwargs),
    get_sun2_summaries=lambda *args, **kwargs: get_sun2_summaries(*args, **kwargs),
    json_value=lambda *args, **kwargs: json_value(*args, **kwargs),
    sun2_product_module_payload=lambda *args, **kwargs: sun2_product_module_payload(*args, **kwargs),
    sun2_sessions_module_payload=lambda *args, **kwargs: sun2_sessions_module_payload(*args, **kwargs),
)
presentation_service = presentation_services.create_service(presentation_dependencies)
add_segment = presentation_service["add_segment"]
age_label = presentation_service["age_label"]
api_bool_state = presentation_service["api_bool_state"]
api_data_quality_row = presentation_service["api_data_quality_row"]
api_day_navigation = presentation_service["api_day_navigation"]
api_detail_field = presentation_service["api_detail_field"]
api_filter = presentation_service["api_filter"]
api_filter_int = presentation_service["api_filter_int"]
api_filter_options = presentation_service["api_filter_options"]
api_filter_value = presentation_service["api_filter_value"]
api_pick = presentation_service["api_pick"]
api_rule_rows = presentation_service["api_rule_rows"]
api_saved_forecast_rows = presentation_service["api_saved_forecast_rows"]
api_tool_row = presentation_service["api_tool_row"]
api_v2_soling_module = presentation_service["api_v2_soling_module"]
apply_common_filters = presentation_service["apply_common_filters"]
clean_display_text = presentation_service["clean_display_text"]
csv_response = presentation_service["csv_response"]
day_zoom_config = presentation_service["day_zoom_config"]
day_zoom_window = presentation_service["day_zoom_window"]
decimate_rows = presentation_service["decimate_rows"]
display_action = presentation_service["display_action"]
display_control_mode = presentation_service["display_control_mode"]
display_segments = presentation_service["display_segments"]
fetch_rows = presentation_service["fetch_rows"]
normalize_month = presentation_service["normalize_month"]
parse_day = presentation_service["parse_day"]
percent_between = presentation_service["percent_between"]
redirect_keep_query = presentation_service["redirect_keep_query"]
redirect_with_query_params = presentation_service["redirect_with_query_params"]
row_to_dict = presentation_service["row_to_dict"]
span_width = presentation_service["span_width"]
total_from_segments = presentation_service["total_from_segments"]
from fibaro_core.services.runtime import notifications as notifications_services
notifications_dependencies = notifications_services.Dependencies(
    NTFY_ACCESS_COOLDOWN_MINUTES=NTFY_ACCESS_COOLDOWN_MINUTES,
    NTFY_ACCESS_TOPIC=NTFY_ACCESS_TOPIC,
    NTFY_BASE_URL=NTFY_BASE_URL,
    NTFY_BOLLARDS_TOPIC=NTFY_BOLLARDS_TOPIC,
    NTFY_DOORS_TOPIC=NTFY_DOORS_TOPIC,
    NTFY_LIGHTS_TOPIC=NTFY_LIGHTS_TOPIC,
    NTFY_OUTBOX_POLL_SECONDS=NTFY_OUTBOX_POLL_SECONDS,
    NTFY_OUTBOX_RETRY_BASE_SECONDS=NTFY_OUTBOX_RETRY_BASE_SECONDS,
    NTFY_OUTBOX_RETRY_MAX_SECONDS=NTFY_OUTBOX_RETRY_MAX_SECONDS,
    NTFY_OUTBOX_STALE_LOCK_SECONDS=NTFY_OUTBOX_STALE_LOCK_SECONDS,
    NTFY_TIMEOUT_SECONDS=NTFY_TIMEOUT_SECONDS,
    NTFY_VENTILATION_TOPIC=NTFY_VENTILATION_TOPIC,
    async_session=async_session,
    logger=logger,
)
notifications_service = notifications_services.create_service(notifications_dependencies)
bollard_mobile_notification_payload = notifications_service["bollard_mobile_notification_payload"]
claim_notification_outbox_row = notifications_service["claim_notification_outbox_row"]
enqueue_ntfy_message = notifications_service["enqueue_ntfy_message"]
finish_notification_outbox_row = notifications_service["finish_notification_outbox_row"]
notification_outbox_row = notifications_service["notification_outbox_row"]
notification_outbox_status = notifications_service["notification_outbox_status"]
notification_outbox_worker = notifications_service["notification_outbox_worker"]
notification_retry_delay_seconds = notifications_service["notification_retry_delay_seconds"]
ntfy_host = notifications_service["ntfy_host"]
ntfy_subscribe_url = notifications_service["ntfy_subscribe_url"]
ntfy_subscription_rows = notifications_service["ntfy_subscription_rows"]
ntfy_topic_url = notifications_service["ntfy_topic_url"]
publish_ntfy_message = notifications_service["publish_ntfy_message"]
save_record = notifications_service["save_record"]
from fibaro_core.services.runtime import system as system_services
system_dependencies = system_services.Dependencies(
    ADMIN_TASK_SEVERITY_SORT=ADMIN_TASK_SEVERITY_SORT,
    FULL_BACKUP_STATUS_PATH=FULL_BACKUP_STATUS_PATH,
    NIGHTLY_BACKUP_STATUS_PATH=NIGHTLY_BACKUP_STATUS_PATH,
    NTFY_ACCESS_COOLDOWN_MINUTES=NTFY_ACCESS_COOLDOWN_MINUTES,
    NTFY_ACCESS_TOPIC=NTFY_ACCESS_TOPIC,
    OPERATIONAL_RETENTION_INITIAL_DELAY_SECONDS=OPERATIONAL_RETENTION_INITIAL_DELAY_SECONDS,
    OPERATIONAL_RETENTION_INTERVAL_HOURS=OPERATIONAL_RETENTION_INTERVAL_HOURS,
    OPERATIONAL_RETENTION_POLICY=OPERATIONAL_RETENTION_POLICY,
    OPERATIONAL_RETENTION_STATE=OPERATIONAL_RETENTION_STATE,
    SUN2_SESSIONS_QUIET_END_HOUR=SUN2_SESSIONS_QUIET_END_HOUR,
    age_label=lambda *args, **kwargs: age_label(*args, **kwargs),
    api_data_quality_row=lambda *args, **kwargs: api_data_quality_row(*args, **kwargs),
    async_session=async_session,
    clear_summary_cache=lambda *args, **kwargs: clear_summary_cache(*args, **kwargs),
    easypark_downloader_status=lambda *args, **kwargs: easypark_downloader_status(*args, **kwargs),
    easypark_next_run_at_from_status=lambda *args, **kwargs: easypark_next_run_at_from_status(*args, **kwargs),
    fallback_car_info_import_status=lambda *args, **kwargs: fallback_car_info_import_status(*args, **kwargs),
    get_parking_sun_link_state=lambda *args, **kwargs: get_parking_sun_link_state(*args, **kwargs),
    ingest_elvia_hours=lambda *args, **kwargs: ingest_elvia_hours(*args, **kwargs),
    latest_energy_reconciliation_check=lambda *args, **kwargs: latest_energy_reconciliation_check(*args, **kwargs),
    logger=logger,
    manual_energy_quickapp_report=lambda *args, **kwargs: manual_energy_quickapp_report(*args, **kwargs),
    minutes_since=lambda *args, **kwargs: minutes_since(*args, **kwargs),
    notification_outbox_status=lambda *args, **kwargs: notification_outbox_status(*args, **kwargs),
    ntfy_subscribe_url=lambda *args, **kwargs: ntfy_subscribe_url(*args, **kwargs),
    ntfy_topic_url=lambda *args, **kwargs: ntfy_topic_url(*args, **kwargs),
    sun2_sessions_active_minutes_since=lambda *args, **kwargs: sun2_sessions_active_minutes_since(*args, **kwargs),
    sunroom_door_alarm_payload=lambda *args, **kwargs: sunroom_door_alarm_payload(*args, **kwargs),
    vehicle_area_not_found_condition=lambda *args, **kwargs: vehicle_area_not_found_condition(*args, **kwargs),
    vehicle_blank_area_condition=lambda *args, **kwargs: vehicle_blank_area_condition(*args, **kwargs),
    vehicle_blank_name_condition=lambda *args, **kwargs: vehicle_blank_name_condition(*args, **kwargs),
    vehicle_missing_area_condition=lambda *args, **kwargs: vehicle_missing_area_condition(*args, **kwargs),
    vehicle_missing_name_condition=lambda *args, **kwargs: vehicle_missing_name_condition(*args, **kwargs),
    vehicle_name_not_found_condition=lambda *args, **kwargs: vehicle_name_not_found_condition(*args, **kwargs),
)
system_service = system_services.create_service(system_dependencies)
admin_keys_context = system_service["admin_keys_context"]
admin_manual_payload = system_service["admin_manual_payload"]
admin_task_import_severity = system_service["admin_task_import_severity"]
api_admin_manual_payload = system_service["api_admin_manual_payload"]
api_admin_task_row = system_service["api_admin_task_row"]
api_import_job_run_row = system_service["api_import_job_run_row"]
api_import_job_status = system_service["api_import_job_status"]
api_import_status_row = system_service["api_import_status_row"]
api_import_status_rows = system_service["api_import_status_rows"]
backup_incident_from_control = system_service["backup_incident_from_control"]
build_admin_data_quality = system_service["build_admin_data_quality"]
build_admin_relation_analysis = system_service["build_admin_relation_analysis"]
build_admin_task_rows = system_service["build_admin_task_rows"]
build_operational_incident_center = system_service["build_operational_incident_center"]
build_reconciliation_control = system_service["build_reconciliation_control"]
cleanup_operational_history_once = system_service["cleanup_operational_history_once"]
correlation_direction = system_service["correlation_direction"]
correlation_strength = system_service["correlation_strength"]
fallback_import_job_status = system_service["fallback_import_job_status"]
import_counts_for_json = system_service["import_counts_for_json"]
import_incident_recommended_action = system_service["import_incident_recommended_action"]
import_job_age = system_service["import_job_age"]
import_job_definition = system_service["import_job_definition"]
import_job_interval_text = system_service["import_job_interval_text"]
import_job_schedule_text = system_service["import_job_schedule_text"]
import_job_status_from_age = system_service["import_job_status_from_age"]
import_job_status_from_minutes = system_service["import_job_status_from_minutes"]
import_job_updated_ago = system_service["import_job_updated_ago"]
import_status_rows = system_service["import_status_rows"]
mark_import_job_running = system_service["mark_import_job_running"]
operational_incident_review_payload = system_service["operational_incident_review_payload"]
operational_retention_worker = system_service["operational_retention_worker"]
pearson_correlation = system_service["pearson_correlation"]
quality_percent = system_service["quality_percent"]
quality_status_from_age = system_service["quality_status_from_age"]
quality_status_from_percent = system_service["quality_status_from_percent"]
read_operational_status_file = system_service["read_operational_status_file"]
record_import_job = system_service["record_import_job"]
run_elvia_import_background = system_service["run_elvia_import_background"]
from fibaro_core.services.runtime import dashboard as dashboard_services
dashboard_dependencies = dashboard_services.Dependencies(
    age_label=lambda *args, **kwargs: age_label(*args, **kwargs),
    async_session=async_session,
    average_value=lambda *args, **kwargs: average_value(*args, **kwargs),
    latest_timestamp_from=lambda *args, **kwargs: latest_timestamp_from(*args, **kwargs),
    normalize_month=lambda *args, **kwargs: normalize_month(*args, **kwargs),
    weather_from_rows=lambda *args, **kwargs: weather_from_rows(*args, **kwargs),
)
dashboard_service = dashboard_services.create_service(dashboard_dependencies)
api_revenue_day = dashboard_service["api_revenue_day"]
api_revenue_overview_tables = dashboard_service["api_revenue_overview_tables"]
api_revenue_summary_row = dashboard_service["api_revenue_summary_row"]
api_revenue_weekly_chart = dashboard_service["api_revenue_weekly_chart"]
build_now_status = dashboard_service["build_now_status"]
build_revenue_month_context = dashboard_service["build_revenue_month_context"]
dashboard_alert = dashboard_service["dashboard_alert"]
dashboard_compare_detail = dashboard_service["dashboard_compare_detail"]
dashboard_compare_value = dashboard_service["dashboard_compare_value"]
dashboard_money_compare = dashboard_service["dashboard_money_compare"]
freshness_item = dashboard_service["freshness_item"]
minutes_since = dashboard_service["minutes_since"]
operating_window = dashboard_service["operating_window"]
operations_area_status = dashboard_service["operations_area_status"]
operations_metric = dashboard_service["operations_metric"]
operations_switch_item = dashboard_service["operations_switch_item"]
from fibaro_core.services.runtime import weather as weather_services
weather_dependencies = weather_services.Dependencies(
    MET_LAT=MET_LAT,
    MET_LON=MET_LON,
    MET_USER_AGENT=MET_USER_AGENT,
    MET_WEATHER_CACHE=MET_WEATHER_CACHE,
    WEATHER_LABELS=WEATHER_LABELS,
    YR_FORECAST_ASSIGNMENTS=YR_FORECAST_ASSIGNMENTS,
    async_session=async_session,
    dedupe_samples_by_bucket=lambda *args, **kwargs: dedupe_samples_by_bucket(*args, **kwargs),
    json_value=lambda *args, **kwargs: json_value(*args, **kwargs),
    logger=logger,
    nested_extra_value=lambda *args, **kwargs: nested_extra_value(*args, **kwargs),
    process_locks=process_locks,
    record_import_job=lambda *args, **kwargs: record_import_job(*args, **kwargs),
)
weather_service = weather_services.create_service(weather_dependencies)
fetch_met_weather = weather_service["fetch_met_weather"]
fetch_yr_cloud_samples = weather_service["fetch_yr_cloud_samples"]
http_header_time = weather_service["http_header_time"]
met_age_seconds = weather_service["met_age_seconds"]
met_details = weather_service["met_details"]
met_entry_at = weather_service["met_entry_at"]
met_forecast_from_payload = weather_service["met_forecast_from_payload"]
met_next_fetch_after = weather_service["met_next_fetch_after"]
met_period_details = weather_service["met_period_details"]
met_period_symbol = weather_service["met_period_symbol"]
met_time = weather_service["met_time"]
met_value = weather_service["met_value"]
met_weather_cached = weather_service["met_weather_cached"]
save_yr_sample_for_payload = weather_service["save_yr_sample_for_payload"]
update_yr_sample_from_forecast = weather_service["update_yr_sample_from_forecast"]
weather_from_rows = weather_service["weather_from_rows"]
weather_label = weather_service["weather_label"]
yr_sample_extra = weather_service["yr_sample_extra"]
yr_sample_from_forecast = weather_service["yr_sample_from_forecast"]
yr_sample_raw = weather_service["yr_sample_raw"]
from fibaro_core.services.runtime import ai as ai_services
ai_dependencies = ai_services.Dependencies(
    AI_CONFIG_KEY=AI_CONFIG_KEY,
    OPENAI_MODEL=OPENAI_MODEL,
    async_session=async_session,
)
ai_service = ai_services.create_service(ai_dependencies)
ai_dataset_overview = ai_service["ai_dataset_overview"]
ai_dataset_schema = ai_service["ai_dataset_schema"]
ai_jsonable = ai_service["ai_jsonable"]
ai_tools_definition = ai_service["ai_tools_definition"]
ask_ai = ai_service["ask_ai"]
effective_openai_settings = ai_service["effective_openai_settings"]
get_ai_config = ai_service["get_ai_config"]
mask_secret = ai_service["mask_secret"]
openai_env_api_key = ai_service["openai_env_api_key"]
openai_responses_request = ai_service["openai_responses_request"]
recent_ai_logs = ai_service["recent_ai_logs"]
response_function_calls = ai_service["response_function_calls"]
response_output_text = ai_service["response_output_text"]
run_ai_tool = ai_service["run_ai_tool"]
run_safe_ai_sql = ai_service["run_safe_ai_sql"]
validate_ai_sql = ai_service["validate_ai_sql"]
from fibaro_core.services.runtime import maintenance as maintenance_services
maintenance_dependencies = maintenance_services.Dependencies(
    MAINTENANCE_ACTION_OPTIONS=MAINTENANCE_ACTION_OPTIONS,
    MAINTENANCE_PRESENCE_OPTIONS=MAINTENANCE_PRESENCE_OPTIONS,
    MAINTENANCE_PRIORITY_OPTIONS=MAINTENANCE_PRIORITY_OPTIONS,
    MAINTENANCE_STATUS_OPTIONS=MAINTENANCE_STATUS_OPTIONS,
    MAINTENANCE_TAG_OPTIONS=MAINTENANCE_TAG_OPTIONS,
    MAINTENANCE_TARGET_OPTIONS=MAINTENANCE_TARGET_OPTIONS,
    OWNTRACKS_LILLETORGET_WAYPOINTS=OWNTRACKS_LILLETORGET_WAYPOINTS,
    OWNTRACKS_SERVICE_URL=OWNTRACKS_SERVICE_URL,
    OWNTRACKS_SITE_VISIT_LOCATION_KEY=OWNTRACKS_SITE_VISIT_LOCATION_KEY,
    OWNTRACKS_SITE_VISIT_LOCATION_NAME=OWNTRACKS_SITE_VISIT_LOCATION_NAME,
    OWNTRACKS_VISIT_SYNC_ENABLED=OWNTRACKS_VISIT_SYNC_ENABLED,
    OWNTRACKS_VISIT_SYNC_INTERVAL_SECONDS=OWNTRACKS_VISIT_SYNC_INTERVAL_SECONDS,
    OWNTRACKS_VISIT_SYNC_LOOKBACK_HOURS=OWNTRACKS_VISIT_SYNC_LOOKBACK_HOURS,
    OWNTRACKS_VISIT_SYNC_TIMEOUT_SECONDS=OWNTRACKS_VISIT_SYNC_TIMEOUT_SECONDS,
    SITE_VISIT_ACTIVE_MAX_HOURS=SITE_VISIT_ACTIVE_MAX_HOURS,
    SITE_VISIT_MAINTENANCE_LINK_MARGIN_MINUTES=SITE_VISIT_MAINTENANCE_LINK_MARGIN_MINUTES,
    async_session=async_session,
    logger=logger,
    process_locks=process_locks,
    record_import_job=lambda *args, **kwargs: record_import_job(*args, **kwargs),
)
maintenance_service = maintenance_services.create_service(maintenance_dependencies)
api_maintenance_log_edit = maintenance_service["api_maintenance_log_edit"]
clean_maintenance_option = maintenance_service["clean_maintenance_option"]
fetch_owntracks_lilletorget_visits = maintenance_service["fetch_owntracks_lilletorget_visits"]
find_site_visit_for_maintenance = maintenance_service["find_site_visit_for_maintenance"]
link_unassigned_maintenance_logs_to_site_visits = maintenance_service["link_unassigned_maintenance_logs_to_site_visits"]
maintenance_datetime_value = maintenance_service["maintenance_datetime_value"]
maintenance_log_row = maintenance_service["maintenance_log_row"]
maintenance_room_value = maintenance_service["maintenance_room_value"]
maintenance_target_name = maintenance_service["maintenance_target_name"]
normalize_maintenance_tags = maintenance_service["normalize_maintenance_tags"]
owntracks_iso_to_local_naive = maintenance_service["owntracks_iso_to_local_naive"]
owntracks_site_visit_sync_worker = maintenance_service["owntracks_site_visit_sync_worker"]
owntracks_visit_request = maintenance_service["owntracks_visit_request"]
record_owntracks_site_visit_sync_failure = maintenance_service["record_owntracks_site_visit_sync_failure"]
run_owntracks_site_visit_sync = maintenance_service["run_owntracks_site_visit_sync"]
site_visit_confidence_percent = maintenance_service["site_visit_confidence_percent"]
site_visit_display_duration = maintenance_service["site_visit_display_duration"]
site_visit_duration_label = maintenance_service["site_visit_duration_label"]
site_visit_is_current = maintenance_service["site_visit_is_current"]
site_visit_is_stale = maintenance_service["site_visit_is_stale"]
site_visit_label = maintenance_service["site_visit_label"]
site_visit_row = maintenance_service["site_visit_row"]
site_visit_status_label = maintenance_service["site_visit_status_label"]
sync_owntracks_site_visits_once = maintenance_service["sync_owntracks_site_visits_once"]
from fibaro_core.services.runtime import control as control_services
control_dependencies = control_services.Dependencies(
    UNIFI_PROTECT_API_TIMEOUT_SECONDS=UNIFI_PROTECT_API_TIMEOUT_SECONDS,
    UNIFI_PROTECT_EVENTS_URL=UNIFI_PROTECT_EVENTS_URL,
    UNIFI_PROTECT_READ_API_TOKEN=UNIFI_PROTECT_READ_API_TOKEN,
)
control_service = control_services.create_service(control_dependencies)
bollard_image_cache_control = control_service["bollard_image_cache_control"]
protect_ledger_client = control_service["protect_ledger_client"]
protect_ledger_json = control_service["protect_ledger_json"]
from fibaro_core.services.runtime import mobile_preview as mobile_preview_services
mobile_preview_dependencies = mobile_preview_services.Dependencies(
    MOBILE_PREVIEW_MONEY_KEYS=MOBILE_PREVIEW_MONEY_KEYS,
    MOBILE_PREVIEW_REFRESH_SECONDS=MOBILE_PREVIEW_REFRESH_SECONDS,
    MOBILE_PREVIEW_SCREENS=MOBILE_PREVIEW_SCREENS,
    mobile_preview_access_key=lambda *args, **kwargs: mobile_preview_access_key(*args, **kwargs),
)
mobile_preview_service = mobile_preview_services.create_service(mobile_preview_dependencies)
mobile_preview_can_view_money = mobile_preview_service["mobile_preview_can_view_money"]
mobile_preview_html = mobile_preview_service["mobile_preview_html"]
mobile_preview_injected_head = mobile_preview_service["mobile_preview_injected_head"]
mobile_preview_screen_payload = mobile_preview_service["mobile_preview_screen_payload"]
mobile_preview_screens_for_request = mobile_preview_service["mobile_preview_screens_for_request"]
render_mobile_preview_screen = mobile_preview_service["render_mobile_preview_screen"]
from fibaro_core.services.runtime import cache as cache_services
cache_dependencies = cache_services.Dependencies(
    SUMMARY_CACHE=SUMMARY_CACHE,
    SUMMARY_CACHE_TTL=SUMMARY_CACHE_TTL,
)
cache_service = cache_services.create_service(cache_dependencies)
cached_summaries = cache_service["cached_summaries"]
clear_summary_cache = cache_service["clear_summary_cache"]
get_energy_summaries = cache_service["get_energy_summaries"]
get_parking_summaries = cache_service["get_parking_summaries"]
get_sun2_summaries = cache_service["get_sun2_summaries"]


# Lifecycle and middleware are registered once, after service construction.
from fibaro_core import lifecycle
lifecycle_dependencies = lifecycle.Dependencies(
    CONFIG_DEFINITIONS=CONFIG_DEFINITIONS,
    FIBARO10_BACKGROUND_TASKS_ENABLED=FIBARO10_BACKGROUND_TASKS_ENABLED,
    FIBARO10_PROCESS_ROLE=FIBARO10_PROCESS_ROLE,
    HC3_DOOR_UNEXPECTED_CHECK_ENABLED=HC3_DOOR_UNEXPECTED_CHECK_ENABLED,
    MASTER_ACCESS_KEY_HASH=MASTER_ACCESS_KEY_HASH,
    OPERATIONAL_RETENTION_ENABLED=OPERATIONAL_RETENTION_ENABLED,
    OWNTRACKS_VISIT_SYNC_ENABLED=OWNTRACKS_VISIT_SYNC_ENABLED,
    ROBOROCK_CONTROL_TOKEN=ROBOROCK_CONTROL_TOKEN,
    SUN2_AXIS_SNAPSHOT_LINK_ENABLED=SUN2_AXIS_SNAPSHOT_LINK_ENABLED,
    SUNBED_POWER_CACHE_WARM_ENABLED=SUNBED_POWER_CACHE_WARM_ENABLED,
    SUNROOM_DOOR_MONITOR_ENABLED=SUNROOM_DOOR_MONITOR_ENABLED,
    SVV_API_KEY=SVV_API_KEY,
    SVV_SYNC_ENABLED=SVV_SYNC_ENABLED,
    access_key_prefix=access_key_prefix,
    access_password_hash=access_password_hash,
    async_session=async_session,
    background_tasks=background_tasks,
    engine=engine,
    ensure_default_roborock_cleaning_profiles=ensure_default_roborock_cleaning_profiles,
    ensure_default_roborock_door_automation=ensure_default_roborock_door_automation,
    ensure_energy_node_backfill=ensure_energy_node_backfill,
    ensure_roborock_schedule_snapshot_backfill=ensure_roborock_schedule_snapshot_backfill,
    get_or_create_config=get_or_create_config,
    hc3_door_poll_worker=hc3_door_poll_worker,
    logger=logger,
    normalize_username=normalize_username,
    notification_outbox_worker=notification_outbox_worker,
    operational_retention_worker=operational_retention_worker,
    owntracks_site_visit_sync_worker=owntracks_site_visit_sync_worker,
    parking_vehicle_svv_worker=parking_vehicle_svv_worker,
    roborock_door_automation_worker=roborock_door_automation_worker,
    seed_energy_circuits=seed_energy_circuits,
    sun2_axis_snapshot_link_worker=sun2_axis_snapshot_link_worker,
    sunbed_power_cache_warm_worker=sunbed_power_cache_warm_worker,
    sunroom_door_monitor_worker=sunroom_door_monitor_worker,
)
lifecycle_handlers = lifecycle.create_handlers(lifecycle_dependencies)
startup = lifecycle_handlers["startup"]
shutdown_application = lifecycle_handlers["shutdown_application"]
from fibaro_core import middleware
middleware_dependencies = middleware.Dependencies(
    SECURITY_HSTS_ENABLED=SECURITY_HSTS_ENABLED,
    SECURITY_HSTS_MAX_AGE_SECONDS=SECURITY_HSTS_MAX_AGE_SECONDS,
    SLOW_REQUEST_WARNING_MS=SLOW_REQUEST_WARNING_MS,
    access_role=access_role,
    find_access_key=find_access_key,
    find_auth_session=find_auth_session,
    has_car_info_app_access=has_car_info_app_access,
    has_koble_worker_access=has_koble_worker_access,
    is_car_info_app_request_path=is_car_info_app_request_path,
    is_koble_worker_request_path=is_koble_worker_request_path,
    is_public_request=is_public_request,
    log_access_attempt=log_access_attempt,
    logger=logger,
    presented_credentials=presented_credentials,
    presented_session_token=presented_session_token,
    templates=templates,
    wants_html=wants_html,
)
middleware_handlers = middleware.create_handlers(middleware_dependencies)
access_key_middleware = middleware_handlers["access_key_middleware"]
security_headers_middleware = middleware_handlers["security_headers_middleware"]
app.middleware("http")(access_key_middleware)
app.middleware("http")(security_headers_middleware)

# HTTP composition. Route order is part of the public contract.
from fibaro_core.routers import control_routes
control_http = control_routes.create_router(control_routes.Dependencies(
    ALARM_APP_URL=ALARM_APP_URL,
    DOOR_SENSOR_CONFIG=DOOR_SENSOR_CONFIG,
    DOOR_SENSOR_IDS=DOOR_SENSOR_IDS,
    NTFY_BOLLARDS_TOPIC=NTFY_BOLLARDS_TOPIC,
    async_session=async_session,
    bollard_image_cache_control=bollard_image_cache_control,
    bollard_mobile_notification_payload=bollard_mobile_notification_payload,
    door_age_label=door_age_label,
    door_change_rows=door_change_rows,
    door_change_text=door_change_text,
    door_config_device_key=door_config_device_key,
    door_event_payload=door_event_payload,
    door_open_periods=door_open_periods,
    door_period_device_key=door_period_device_key,
    door_status_payload=door_status_payload,
    latest_door_event_by_device=latest_door_event_by_device,
    logger=logger,
    parse_day=parse_day,
    protect_ledger_client=protect_ledger_client,
    protect_ledger_json=protect_ledger_json,
    publish_ntfy_message=publish_ntfy_message,
    row_to_dict=row_to_dict,
    run_hc3_door_poll_once=run_hc3_door_poll_once,
    sunroom_bed_id_for_config=sunroom_bed_id_for_config,
    sunroom_bed_status_payload=sunroom_bed_status_payload,
    sunroom_door_alarm_payload=sunroom_door_alarm_payload,
    sunroom_door_session_payload=sunroom_door_session_payload,
    sunroom_logic_payload=sunroom_logic_payload,
    sunroom_room_detail_payload=sunroom_room_detail_payload,
    sunroom_room_overview_payload=sunroom_room_overview_payload,
))
api_hc3_door_events_json = control_http.endpoints["api_hc3_door_events_json"]
api_hc3_doors_alarm = control_http.endpoints["api_hc3_doors_alarm"]
api_hc3_doors_poll_sync = control_http.endpoints["api_hc3_doors_poll_sync"]
api_hc3_doors_status = control_http.endpoints["api_hc3_doors_status"]
api_hc3_doors_sunroom_logic = control_http.endpoints["api_hc3_doors_sunroom_logic"]
api_hc3_doors_sunroom_overview = control_http.endpoints["api_hc3_doors_sunroom_overview"]
api_hc3_doors_sunroom_room_detail = control_http.endpoints["api_hc3_doors_sunroom_room_detail"]
api_hc3_doors_sunroom_sessions = control_http.endpoints["api_hc3_doors_sunroom_sessions"]
api_test_unifi_protect_bollard_mobile_notification = control_http.endpoints["api_test_unifi_protect_bollard_mobile_notification"]
api_unifi_protect_bollard_asset_image = control_http.endpoints["api_unifi_protect_bollard_asset_image"]
api_unifi_protect_bollard_baseline = control_http.endpoints["api_unifi_protect_bollard_baseline"]
api_unifi_protect_bollard_camera_crop = control_http.endpoints["api_unifi_protect_bollard_camera_crop"]
api_unifi_protect_bollard_camera_image = control_http.endpoints["api_unifi_protect_bollard_camera_image"]
api_unifi_protect_bollard_incident_image = control_http.endpoints["api_unifi_protect_bollard_incident_image"]
api_unifi_protect_bollard_mobile_notifications = control_http.endpoints["api_unifi_protect_bollard_mobile_notifications"]
api_unifi_protect_bollards = control_http.endpoints["api_unifi_protect_bollards"]
api_unifi_protect_cameras = control_http.endpoints["api_unifi_protect_cameras"]
api_unifi_protect_capabilities = control_http.endpoints["api_unifi_protect_capabilities"]
api_unifi_protect_daily_license_plates = control_http.endpoints["api_unifi_protect_daily_license_plates"]
api_unifi_protect_events = control_http.endpoints["api_unifi_protect_events"]
api_unifi_protect_recognition_detail = control_http.endpoints["api_unifi_protect_recognition_detail"]
api_unifi_protect_recognition_snapshot = control_http.endpoints["api_unifi_protect_recognition_snapshot"]
api_unifi_protect_recognitions = control_http.endpoints["api_unifi_protect_recognitions"]
api_unifi_protect_snapshot = control_http.endpoints["api_unifi_protect_snapshot"]
api_unifi_protect_stats = control_http.endpoints["api_unifi_protect_stats"]
api_unifi_protect_status = control_http.endpoints["api_unifi_protect_status"]
from fibaro_core.routers import parking_routes
parking_http = parking_routes.create_router(parking_routes.Dependencies(
    CARS_DAY_CACHE_TTL=CARS_DAY_CACHE_TTL,
    CARS_HISTORY_CACHE_TTL=CARS_HISTORY_CACHE_TTL,
    SUMMARY_CACHE=SUMMARY_CACHE,
    SVV_API_KEY=SVV_API_KEY,
    SVV_IMPORT_SYNC_BATCH_SIZE=SVV_IMPORT_SYNC_BATCH_SIZE,
    SVV_SYNC_BATCH_SIZE=SVV_SYNC_BATCH_SIZE,
    SVV_SYNC_ENABLED=SVV_SYNC_ENABLED,
    api_detail_field=api_detail_field,
    api_parking_time_distribution=api_parking_time_distribution,
    async_session=async_session,
    build_parking_forecast=build_parking_forecast,
    car_info_lookup_request=car_info_lookup_request,
    clear_parking_vehicle_not_found_area=clear_parking_vehicle_not_found_area,
    clear_parking_vehicle_not_found_fields=clear_parking_vehicle_not_found_fields,
    clear_summary_cache=clear_summary_cache,
    easypark_downloader_request=easypark_downloader_request,
    easypark_recent_period=easypark_recent_period,
    get_parking_summaries=get_parking_summaries,
    import_counts_for_json=import_counts_for_json,
    import_job_definition=import_job_definition,
    import_job_status_from_age=import_job_status_from_age,
    ingest_easypark_csv=ingest_easypark_csv,
    is_not_found_marker=is_not_found_marker,
    logger=logger,
    normalize_month=normalize_month,
    parking_area_overview_data=parking_area_overview_data,
    parking_car_info_candidate_rows=parking_car_info_candidate_rows,
    parking_missing_area_rows=parking_missing_area_rows,
    parking_missing_name_rows=parking_missing_name_rows,
    parking_period_summary=parking_period_summary,
    parking_row_api=parking_row_api,
    parking_timeline_end=parking_timeline_end,
    parking_vehicle_by_plate_or_compact=parking_vehicle_by_plate_or_compact,
    parking_vehicle_lookup_payload=parking_vehicle_lookup_payload,
    parking_vehicle_not_found_field_labels=parking_vehicle_not_found_field_labels,
    parking_weekly_average_payload=parking_weekly_average_payload,
    parking_weekly_average_period=parking_weekly_average_period,
    parking_weekly_selected_years=parking_weekly_selected_years,
    parking_weekly_year_comparison_payload=parking_weekly_year_comparison_payload,
    parse_day=parse_day,
    protect_ledger_json=protect_ledger_json,
    record_import_job=record_import_job,
    redirect_keep_query=redirect_keep_query,
    redirect_with_query_params=redirect_with_query_params,
    refresh_parking_vehicle_summary=refresh_parking_vehicle_summary,
    require_settings_access=require_settings_access,
    require_settings_or_car_info_access=require_settings_or_car_info_access,
    run_vehicle_svv_sync=run_vehicle_svv_sync,
    save_parking_forecast_after_import=save_parking_forecast_after_import,
    templates=templates,
    unpaid_registered_vehicle_stays_payload=unpaid_registered_vehicle_stays_payload,
    vehicle_blank_area_condition=vehicle_blank_area_condition,
    vehicle_blank_name_condition=vehicle_blank_name_condition,
    vehicle_car_info_candidate_condition=vehicle_car_info_candidate_condition,
    vehicle_car_info_country_condition=vehicle_car_info_country_condition,
    vehicle_missing_area_condition=vehicle_missing_area_condition,
    vehicle_missing_name_condition=vehicle_missing_name_condition,
))
api_cars_day = parking_http.endpoints["api_cars_day"]
api_cars_day_detections = parking_http.endpoints["api_cars_day_detections"]
api_parking_control_report = parking_http.endpoints["api_parking_control_report"]
api_v2_fetch_parking_settlements = parking_http.endpoints["api_v2_fetch_parking_settlements"]
api_v2_parking_car_info_sync = parking_http.endpoints["api_v2_parking_car_info_sync"]
api_v2_parking_clear_area_not_found = parking_http.endpoints["api_v2_parking_clear_area_not_found"]
api_v2_parking_refresh = parking_http.endpoints["api_v2_parking_refresh"]
api_v2_parking_save_forecast = parking_http.endpoints["api_v2_parking_save_forecast"]
api_v2_parking_svv_sync = parking_http.endpoints["api_v2_parking_svv_sync"]
api_v2_parking_time_distribution = parking_http.endpoints["api_v2_parking_time_distribution"]
api_v2_parking_vehicle_clear_not_found = parking_http.endpoints["api_v2_parking_vehicle_clear_not_found"]
api_v2_parking_vehicle_detail = parking_http.endpoints["api_v2_parking_vehicle_detail"]
api_v2_parking_weekly_average_years = parking_http.endpoints["api_v2_parking_weekly_average_years"]
api_v2_parking_weekly_averages = parking_http.endpoints["api_v2_parking_weekly_averages"]
api_v2_parking_year_comparison = parking_http.endpoints["api_v2_parking_year_comparison"]
classic_parking_area_lookup_view = parking_http.endpoints["classic_parking_area_lookup_view"]
classic_parking_name_lookup_view = parking_http.endpoints["classic_parking_name_lookup_view"]
classic_parking_vehicle_detail_view = parking_http.endpoints["classic_parking_vehicle_detail_view"]
classic_parking_vehicles_view = parking_http.endpoints["classic_parking_vehicles_view"]
parking_area_lookup_view = parking_http.endpoints["parking_area_lookup_view"]
parking_area_overview_view = parking_http.endpoints["parking_area_overview_view"]
parking_car_info_candidates_api = parking_http.endpoints["parking_car_info_candidates_api"]
parking_easypark_import_csv = parking_http.endpoints["parking_easypark_import_csv"]
parking_forecast_save = parking_http.endpoints["parking_forecast_save"]
parking_forecast_view = parking_http.endpoints["parking_forecast_view"]
parking_missing_areas_api = parking_http.endpoints["parking_missing_areas_api"]
parking_missing_names_api = parking_http.endpoints["parking_missing_names_api"]
parking_name_lookup_view = parking_http.endpoints["parking_name_lookup_view"]
parking_overview_view = parking_http.endpoints["parking_overview_view"]
parking_redirect = parking_http.endpoints["parking_redirect"]
parking_refresh = parking_http.endpoints["parking_refresh"]
parking_sessions_view = parking_http.endpoints["parking_sessions_view"]
parking_statistics_view = parking_http.endpoints["parking_statistics_view"]
parking_vehicle_area_api = parking_http.endpoints["parking_vehicle_area_api"]
parking_vehicle_car_info_api = parking_http.endpoints["parking_vehicle_car_info_api"]
parking_vehicle_clear_not_found_area = parking_http.endpoints["parking_vehicle_clear_not_found_area"]
parking_vehicle_detail_save = parking_http.endpoints["parking_vehicle_detail_save"]
parking_vehicle_detail_view = parking_http.endpoints["parking_vehicle_detail_view"]
parking_vehicle_name_api = parking_http.endpoints["parking_vehicle_name_api"]
parking_vehicle_statistics_view = parking_http.endpoints["parking_vehicle_statistics_view"]
parking_vehicle_svv_sync_api = parking_http.endpoints["parking_vehicle_svv_sync_api"]
parking_vehicles_view = parking_http.endpoints["parking_vehicles_view"]
from fibaro_core.routers import system_routes
system_http = system_routes.create_router(system_routes.Dependencies(
    ACCESS_LOG_FAILURE_RETENTION_DAYS=ACCESS_LOG_FAILURE_RETENTION_DAYS,
    ACCESS_LOG_SUCCESS_RETENTION_DAYS=ACCESS_LOG_SUCCESS_RETENTION_DAYS,
    AI_CONFIG_KEY=AI_CONFIG_KEY,
    APP_COMMIT=APP_COMMIT,
    APP_STARTED_AT=APP_STARTED_AT,
    AUTH_SESSION_RETENTION_DAYS=AUTH_SESSION_RETENTION_DAYS,
    FIBARO10_BACKGROUND_TASKS_ENABLED=FIBARO10_BACKGROUND_TASKS_ENABLED,
    FIBARO10_PROCESS_ROLE=FIBARO10_PROCESS_ROLE,
    IMPORT_JOB_FAILURE_RETENTION_DAYS=IMPORT_JOB_FAILURE_RETENTION_DAYS,
    IMPORT_JOB_SUCCESS_RETENTION_DAYS=IMPORT_JOB_SUCCESS_RETENTION_DAYS,
    MOBILE_PREVIEW_REFRESH_SECONDS=MOBILE_PREVIEW_REFRESH_SECONDS,
    NOTIFICATION_SENT_RETENTION_DAYS=NOTIFICATION_SENT_RETENTION_DAYS,
    NTFY_BASE_URL=NTFY_BASE_URL,
    OPENAI_MODEL=OPENAI_MODEL,
    OPERATIONAL_RETENTION_ENABLED=OPERATIONAL_RETENTION_ENABLED,
    OPERATIONAL_RETENTION_INTERVAL_HOURS=OPERATIONAL_RETENTION_INTERVAL_HOURS,
    OPERATIONAL_RETENTION_STATE=OPERATIONAL_RETENTION_STATE,
    admin_manual_payload=admin_manual_payload,
    ai_dataset_overview=ai_dataset_overview,
    ask_ai=ask_ai,
    async_session=async_session,
    background_tasks=background_tasks,
    build_operational_incident_center=build_operational_incident_center,
    csv_response=csv_response,
    effective_openai_settings=effective_openai_settings,
    import_status_rows=import_status_rows,
    incident_state=incident_state,
    logger=logger,
    mask_secret=mask_secret,
    minutes_since=minutes_since,
    mobile_preview_screen_payload=mobile_preview_screen_payload,
    mobile_preview_screens_for_request=mobile_preview_screens_for_request,
    notification_outbox_status=notification_outbox_status,
    ntfy_host=ntfy_host,
    ntfy_subscription_rows=ntfy_subscription_rows,
    operational_incident_review_payload=operational_incident_review_payload,
    parse_form_body=parse_form_body,
    protect_ledger_json=protect_ledger_json,
    recent_ai_logs=recent_ai_logs,
    redirect_keep_query=redirect_keep_query,
    render_mobile_preview_screen=render_mobile_preview_screen,
    require_settings_access=require_settings_access,
    row_to_dict=row_to_dict,
    templates=templates,
))
account_build_view = system_http.endpoints["account_build_view"]
account_manual_view = system_http.endpoints["account_manual_view"]
account_technical_view = system_http.endpoints["account_technical_view"]
account_view = system_http.endpoints["account_view"]
ai_datasets_json = system_http.endpoints["ai_datasets_json"]
ai_logs_json = system_http.endpoints["ai_logs_json"]
ai_redirect = system_http.endpoints["ai_redirect"]
ai_search_submit = system_http.endpoints["ai_search_submit"]
ai_search_view = system_http.endpoints["ai_search_view"]
ai_settings_update = system_http.endpoints["ai_settings_update"]
ai_settings_view = system_http.endpoints["ai_settings_view"]
api_admin_build = system_http.endpoints["api_admin_build"]
api_admin_builds = system_http.endpoints["api_admin_builds"]
api_admin_manual = system_http.endpoints["api_admin_manual"]
api_manual = system_http.endpoints["api_manual"]
api_mobile_preview_frame = system_http.endpoints["api_mobile_preview_frame"]
api_mobile_preview_screens = system_http.endpoints["api_mobile_preview_screens"]
api_system_incident_review = system_http.endpoints["api_system_incident_review"]
api_system_notifications = system_http.endpoints["api_system_notifications"]
api_system_search = system_http.endpoints["api_system_search"]
api_system_subsystems = system_http.endpoints["api_system_subsystems"]
events_json = system_http.endpoints["events_json"]
favicon = system_http.endpoints["favicon"]
generic_download = system_http.endpoints["generic_download"]
health = system_http.endpoints["health"]
root_service_info = system_http.endpoints["root_service_info"]
from fibaro_core.routers import access_routes
access_http = access_routes.create_router(access_routes.Dependencies(
    AUTH_COOKIE_NAME=AUTH_COOKIE_NAME,
    AUTH_SESSION_MAX_AGE_SECONDS=AUTH_SESSION_MAX_AGE_SECONDS,
    AUTH_USER_COOKIE_NAME=AUTH_USER_COOKIE_NAME,
    FIBARO10_PWA=FIBARO10_PWA,
    access_key_prefix=access_key_prefix,
    access_password_hash=access_password_hash,
    access_role=access_role,
    access_role_label=access_role_label,
    async_session=async_session,
    create_auth_session=create_auth_session,
    find_access_key=find_access_key,
    log_access_attempt=log_access_attempt,
    normalize_username=normalize_username,
    parse_form_body=parse_form_body,
    redirect_keep_query=redirect_keep_query,
    require_master=require_master,
    revoke_auth_session=revoke_auth_session,
    should_use_secure_cookie=should_use_secure_cookie,
    templates=templates,
))
api_auth_me = access_http.endpoints["api_auth_me"]
api_auth_session_create = access_http.endpoints["api_auth_session_create"]
api_auth_session_delete = access_http.endpoints["api_auth_session_delete"]
api_v2_admin_user_create = access_http.endpoints["api_v2_admin_user_create"]
api_v2_admin_user_update = access_http.endpoints["api_v2_admin_user_update"]
keys_create = access_http.endpoints["keys_create"]
keys_disable = access_http.endpoints["keys_disable"]
keys_enable = access_http.endpoints["keys_enable"]
keys_role_update = access_http.endpoints["keys_role_update"]
keys_view = access_http.endpoints["keys_view"]
login_submit = access_http.endpoints["login_submit"]
login_view = access_http.endpoints["login_view"]
logout = access_http.endpoints["logout"]
from fibaro_core.routers import building_routes
building_http = building_routes.create_router(building_routes.Dependencies(
    CONFIG_DEFINITIONS=CONFIG_DEFINITIONS,
    async_session=async_session,
    build_light_chart_markers=build_light_chart_markers,
    build_lux_day=build_lux_day,
    build_temp_day=build_temp_day,
    config_payload=config_payload,
    config_values_from_payload=config_values_from_payload,
    csv_response=csv_response,
    fetch_lux_samples=fetch_lux_samples,
    fetch_rows=fetch_rows,
    get_or_create_config=get_or_create_config,
    parse_day=parse_day,
    percent_between=percent_between,
    redirect_keep_query=redirect_keep_query,
    require_settings_access=require_settings_access,
    row_to_dict=row_to_dict,
    templates=templates,
    validate_config_values=validate_config_values,
))
api_control_config = building_http.endpoints["api_control_config"]
api_control_config_update = building_http.endpoints["api_control_config_update"]
api_control_configs = building_http.endpoints["api_control_configs"]
classic_light_settings_view = building_http.endpoints["classic_light_settings_view"]
day_lux_view = building_http.endpoints["day_lux_view"]
day_temp_view = building_http.endpoints["day_temp_view"]
light_samples_download = building_http.endpoints["light_samples_download"]
light_samples_json = building_http.endpoints["light_samples_json"]
light_samples_view = building_http.endpoints["light_samples_view"]
lights_download = building_http.endpoints["lights_download"]
lights_json = building_http.endpoints["lights_json"]
lights_redirect = building_http.endpoints["lights_redirect"]
lights_view = building_http.endpoints["lights_view"]
ventilation_download = building_http.endpoints["ventilation_download"]
ventilation_json = building_http.endpoints["ventilation_json"]
ventilation_redirect = building_http.endpoints["ventilation_redirect"]
ventilation_samples_download = building_http.endpoints["ventilation_samples_download"]
ventilation_samples_json = building_http.endpoints["ventilation_samples_json"]
ventilation_samples_view = building_http.endpoints["ventilation_samples_view"]
ventilation_view = building_http.endpoints["ventilation_view"]
yr_samples_download = building_http.endpoints["yr_samples_download"]
yr_samples_json = building_http.endpoints["yr_samples_json"]
yr_samples_view = building_http.endpoints["yr_samples_view"]
from fibaro_core.routers import energy_routes
energy_http = energy_routes.create_router(energy_routes.Dependencies(
    ENERGY_HC3_HOURLY_DISPLAY_OFFSET=ENERGY_HC3_HOURLY_DISPLAY_OFFSET,
    HC3_ENERGY_LIVE_TIMEOUT_SECONDS=HC3_ENERGY_LIVE_TIMEOUT_SECONDS,
    __file__=__file__,
    async_session=async_session,
    clean_energy_load_values=clean_energy_load_values,
    clean_energy_node_values=clean_energy_node_values,
    default_energy_node_name=default_energy_node_name,
    energy_area_cards=energy_area_cards,
    energy_node_branch_ids=energy_node_branch_ids,
    energy_node_from_values=energy_node_from_values,
    find_or_create_energy_node_for_load=find_or_create_energy_node_for_load,
    get_energy_summaries=get_energy_summaries,
    hc3_devices_request=hc3_devices_request,
    hc3_energy_device_summary=hc3_energy_device_summary,
    hc3_energy_nodes_live=hc3_energy_nodes_live,
    load_sunbed_power_analysis=load_sunbed_power_analysis,
    mark_import_job_running=mark_import_job_running,
    parse_day=parse_day,
    redirect_keep_query=redirect_keep_query,
    redirect_with_query_params=redirect_with_query_params,
    require_settings_access=require_settings_access,
    row_to_dict=row_to_dict,
    run_elvia_import_background=run_elvia_import_background,
    templates=templates,
    validate_energy_load_power_values=validate_energy_load_power_values,
    validate_energy_node_hc3_values=validate_energy_node_hc3_values,
    validate_energy_node_link_uniqueness=validate_energy_node_link_uniqueness,
    validate_energy_node_parent=validate_energy_node_parent,
    validate_energy_node_profile_values=validate_energy_node_profile_values,
))
api_energy_elvia_upload = energy_http.endpoints["api_energy_elvia_upload"]
api_v2_energy_circuit_update = energy_http.endpoints["api_v2_energy_circuit_update"]
api_v2_energy_hc3_devices = energy_http.endpoints["api_v2_energy_hc3_devices"]
api_v2_energy_load_create = energy_http.endpoints["api_v2_energy_load_create"]
api_v2_energy_load_update = energy_http.endpoints["api_v2_energy_load_update"]
api_v2_energy_node_create = energy_http.endpoints["api_v2_energy_node_create"]
api_v2_energy_node_update = energy_http.endpoints["api_v2_energy_node_update"]
api_v2_energy_nodes_live = energy_http.endpoints["api_v2_energy_nodes_live"]
classic_energy_circuits_pdf = energy_http.endpoints["classic_energy_circuits_pdf"]
classic_energy_loads_pdf = energy_http.endpoints["classic_energy_loads_pdf"]
energy_circuit_save = energy_http.endpoints["energy_circuit_save"]
energy_circuits_pdf = energy_http.endpoints["energy_circuits_pdf"]
energy_circuits_view = energy_http.endpoints["energy_circuits_view"]
energy_elvia_json = energy_http.endpoints["energy_elvia_json"]
energy_elvia_upload = energy_http.endpoints["energy_elvia_upload"]
energy_elvia_view = energy_http.endpoints["energy_elvia_view"]
energy_fibaro_json = energy_http.endpoints["energy_fibaro_json"]
energy_load_save = energy_http.endpoints["energy_load_save"]
energy_load_toggle_active = energy_http.endpoints["energy_load_toggle_active"]
energy_loads_pdf = energy_http.endpoints["energy_loads_pdf"]
energy_loads_view = energy_http.endpoints["energy_loads_view"]
energy_overview_legacy_redirect = energy_http.endpoints["energy_overview_legacy_redirect"]
energy_redirect = energy_http.endpoints["energy_redirect"]
energy_status_view = energy_http.endpoints["energy_status_view"]
energy_sunbed_consumption_view = energy_http.endpoints["energy_sunbed_consumption_view"]
energy_view = energy_http.endpoints["energy_view"]
from fibaro_core.routers import sun_routes
sun_http = sun_routes.create_router(sun_routes.Dependencies(
    SUMMARY_CACHE=SUMMARY_CACHE,
    SUMMARY_CACHE_TTL=SUMMARY_CACHE_TTL,
    SUN2_AXIS_SNAPSHOT_TOLERANCE_SECONDS=SUN2_AXIS_SNAPSHOT_TOLERANCE_SECONDS,
    async_session=async_session,
    axis_snapshot_browser_payload=axis_snapshot_browser_payload,
    axis_snapshot_path_for_id=axis_snapshot_path_for_id,
    backfill_sun2_room_identity=backfill_sun2_room_identity,
    build_sun2_forecast=build_sun2_forecast,
    clear_summary_cache=clear_summary_cache,
    get_sun2_session_database_total=get_sun2_session_database_total,
    get_sun2_session_options=get_sun2_session_options,
    get_sun2_summaries=get_sun2_summaries,
    parse_axis_snapshot_id=parse_axis_snapshot_id,
    primary_sun2_session_image=primary_sun2_session_image,
    redirect_keep_query=redirect_keep_query,
    replace_sun2_session_image_with_axis_snapshot=replace_sun2_session_image_with_axis_snapshot,
    require_settings_access=require_settings_access,
    row_to_dict=row_to_dict,
    run_sun2_axis_snapshot_link_once=run_sun2_axis_snapshot_link_once,
    set_sun2_session_primary_image=set_sun2_session_primary_image,
    sun2_session_image_meta_options=sun2_session_image_meta_options,
    templates=templates,
))
api_sun2_axis_snapshot_image = sun_http.endpoints["api_sun2_axis_snapshot_image"]
api_sun2_session_image_browser = sun_http.endpoints["api_sun2_session_image_browser"]
api_sun2_session_select_image = sun_http.endpoints["api_sun2_session_select_image"]
api_sun2_session_set_primary_image = sun_http.endpoints["api_sun2_session_set_primary_image"]
api_v2_sun2_link_snapshot_images = sun_http.endpoints["api_v2_sun2_link_snapshot_images"]
api_v2_sun2_save_forecast = sun_http.endpoints["api_v2_sun2_save_forecast"]
api_v2_sun2_year_comparison = sun_http.endpoints["api_v2_sun2_year_comparison"]
api_v2_sun_settlement_attachment = sun_http.endpoints["api_v2_sun_settlement_attachment"]
api_v2_sun_settlement_detail = sun_http.endpoints["api_v2_sun_settlement_detail"]
api_v2_upload_sun_settlement = sun_http.endpoints["api_v2_upload_sun_settlement"]
energy_soling_legacy_redirect = sun_http.endpoints["energy_soling_legacy_redirect"]
sun2_backfill_room_identity = sun_http.endpoints["sun2_backfill_room_identity"]
sun2_beds_json = sun_http.endpoints["sun2_beds_json"]
sun2_beds_view = sun_http.endpoints["sun2_beds_view"]
sun2_day_timeline_view = sun_http.endpoints["sun2_day_timeline_view"]
sun2_forecast_save = sun_http.endpoints["sun2_forecast_save"]
sun2_forecast_view = sun_http.endpoints["sun2_forecast_view"]
sun2_members_json = sun_http.endpoints["sun2_members_json"]
sun2_members_view = sun_http.endpoints["sun2_members_view"]
sun2_overview_view = sun_http.endpoints["sun2_overview_view"]
sun2_redirect = sun_http.endpoints["sun2_redirect"]
sun2_room_stats_json = sun_http.endpoints["sun2_room_stats_json"]
sun2_room_stats_json_legacy_redirect = sun_http.endpoints["sun2_room_stats_json_legacy_redirect"]
sun2_room_stats_legacy_redirect = sun_http.endpoints["sun2_room_stats_legacy_redirect"]
sun2_room_stats_view = sun_http.endpoints["sun2_room_stats_view"]
sun2_session_image = sun_http.endpoints["sun2_session_image"]
sun2_session_image_item = sun_http.endpoints["sun2_session_image_item"]
sun2_sessions_json = sun_http.endpoints["sun2_sessions_json"]
sun2_sessions_view = sun_http.endpoints["sun2_sessions_view"]
from fibaro_core.routers import revenue_routes
revenue_http = revenue_routes.create_router(revenue_routes.Dependencies(
    DAY_ZOOM_OPTIONS=DAY_ZOOM_OPTIONS,
    DREAME_EXPECTED_ROBOT_NAME=DREAME_EXPECTED_ROBOT_NAME,
    LIGHT_TIMELINE_DEVICES=LIGHT_TIMELINE_DEVICES,
    NTFY_LIGHTS_TOPIC=NTFY_LIGHTS_TOPIC,
    NTFY_VENTILATION_TOPIC=NTFY_VENTILATION_TOPIC,
    VENT_TIMELINE_DEVICES=VENT_TIMELINE_DEVICES,
    api_bool_state=api_bool_state,
    api_hc3_doors_status=lambda *args, **kwargs: api_hc3_doors_status(*args, **kwargs),
    api_revenue_day=api_revenue_day,
    api_unifi_protect_bollards=lambda *args, **kwargs: api_unifi_protect_bollards(*args, **kwargs),
    async_session=async_session,
    build_light_timeline_group=build_light_timeline_group,
    build_lux_sparkline=build_lux_sparkline,
    build_now_status=build_now_status,
    build_revenue_month_context=build_revenue_month_context,
    build_timeline_group=build_timeline_group,
    dashboard_alert=dashboard_alert,
    dashboard_compare_value=dashboard_compare_value,
    dashboard_money_compare=dashboard_money_compare,
    day_zoom_window=day_zoom_window,
    event_device_key=event_device_key,
    freshness_item=freshness_item,
    get_parking_summaries=get_parking_summaries,
    get_sun2_summaries=get_sun2_summaries,
    hc3_fetch_switch_statuses=hc3_fetch_switch_statuses,
    hc3_switch_config_for_timeline_device=hc3_switch_config_for_timeline_device,
    import_status_rows=import_status_rows,
    latest_cleaning_robot_sample=latest_cleaning_robot_sample,
    light_sample_state=light_sample_state,
    minutes_since=minutes_since,
    ntfy_subscribe_url=ntfy_subscribe_url,
    ntfy_topic_url=ntfy_topic_url,
    operating_window=operating_window,
    operations_area_status=operations_area_status,
    operations_metric=operations_metric,
    operations_recent_door_items=operations_recent_door_items,
    operations_switch_item=operations_switch_item,
    parse_day=parse_day,
    percent_between=percent_between,
    state_from_event=state_from_event,
    status_timeline_lane=status_timeline_lane,
    templates=templates,
    ventilation_status_payload=ventilation_status_payload,
    weather_from_rows=weather_from_rows,
))
api_operations_overview = revenue_http.endpoints["api_operations_overview"]
api_v2_overview = revenue_http.endpoints["api_v2_overview"]
api_v2_revenue_month = revenue_http.endpoints["api_v2_revenue_month"]
api_v2_revenue_year_comparison = revenue_http.endpoints["api_v2_revenue_year_comparison"]
api_v2_settlement_attachment = revenue_http.endpoints["api_v2_settlement_attachment"]
api_v2_settlement_detail = revenue_http.endpoints["api_v2_settlement_detail"]
api_v2_status_comparison = revenue_http.endpoints["api_v2_status_comparison"]
day_view = revenue_http.endpoints["day_view"]
import_status_view = revenue_http.endpoints["import_status_view"]
index = revenue_http.endpoints["index"]
status_key_metrics_view = revenue_http.endpoints["status_key_metrics_view"]
status_revenue_month_view = revenue_http.endpoints["status_revenue_month_view"]
status_statistics_view = revenue_http.endpoints["status_statistics_view"]
from fibaro_core.routers import modules_routes
from functools import partial
from fibaro_core.services.modules import revenue as revenue_module
revenue_module_dependencies = revenue_module.Dependencies(
    api_revenue_accumulated_year_chart=api_revenue_accumulated_year_chart,
    api_revenue_overview_tables=api_revenue_overview_tables,
    api_revenue_weekly_chart=api_revenue_weekly_chart,
    get_parking_summaries=get_parking_summaries,
    get_sun2_summaries=get_sun2_summaries,
    parking_period_summary=parking_period_summary,
)
from fibaro_core.services.modules import linking as linking_module
linking_module_dependencies = linking_module.Dependencies(
    PARKING_SUN_LINK_CONFIRMED=PARKING_SUN_LINK_CONFIRMED,
    PARKING_SUN_LINK_PENDING=PARKING_SUN_LINK_PENDING,
    api_filter=api_filter,
    api_filter_int=api_filter_int,
    api_parking_sun_link_candidate_row=api_parking_sun_link_candidate_row,
    api_parking_sun_link_match_row=api_parking_sun_link_match_row,
    api_parking_sun_link_state_row=api_parking_sun_link_state_row,
    get_parking_sun_link_state=get_parking_sun_link_state,
    parking_sun_link_candidate_edit=parking_sun_link_candidate_edit,
    parking_sun_link_matched_paid_totals=parking_sun_link_matched_paid_totals,
    parking_sun_link_qualified_distinct_matched_paid_total=parking_sun_link_qualified_distinct_matched_paid_total,
    parking_sun_link_settings_edit=parking_sun_link_settings_edit,
    refresh_parking_sun_link_state_counts=refresh_parking_sun_link_state_counts,
)
from fibaro_core.services.modules import parking as parking_module
parking_module_dependencies = parking_module.Dependencies(
    api_day_navigation=api_day_navigation,
    api_filter=api_filter,
    api_filter_int=api_filter_int,
    api_filter_options=api_filter_options,
    api_filter_value=api_filter_value,
    api_parking_clear_area_not_found_action=api_parking_clear_area_not_found_action,
    api_parking_day_timeline=api_parking_day_timeline,
    api_parking_default_actions=api_parking_default_actions,
    api_parking_forecast_evolution_chart=api_parking_forecast_evolution_chart,
    api_parking_forecast_rows=api_parking_forecast_rows,
    api_parking_overview_tables=api_parking_overview_tables,
    api_parking_saved_forecast_rows=api_parking_saved_forecast_rows,
    api_parking_weekly_chart=api_parking_weekly_chart,
    api_tool_row=api_tool_row,
    build_parking_forecast=build_parking_forecast,
    get_parking_summaries=get_parking_summaries,
    import_job_age=import_job_age,
    import_job_updated_ago=import_job_updated_ago,
    parking_area_missing_rows_for_period=parking_area_missing_rows_for_period,
    parking_area_overview_data=parking_area_overview_data,
    parking_missing_area_rows=parking_missing_area_rows,
    parking_previous_stats_for_rows=parking_previous_stats_for_rows,
    parking_row_api=parking_row_api,
    parking_vehicle_count_stats=parking_vehicle_count_stats,
    parking_vehicle_row_api=parking_vehicle_row_api,
    parking_vehicle_search_condition=parking_vehicle_search_condition,
    parse_day=parse_day,
    row_to_dict=row_to_dict,
)
from fibaro_core.services.modules import sun as sun_module
sun_module_dependencies = sun_module.Dependencies(
    api_v2_soling_module=api_v2_soling_module,
)
from fibaro_core.services.modules import energy as energy_module
energy_module_dependencies = energy_module.Dependencies(
    api_config_value_rows=api_config_value_rows,
    api_day_navigation=api_day_navigation,
    api_energy_circuit_edit=api_energy_circuit_edit,
    api_energy_load_edit=api_energy_load_edit,
    api_filter=api_filter,
    api_filter_int=api_filter_int,
    api_filter_options=api_filter_options,
    api_filter_value=api_filter_value,
    api_pick=api_pick,
    api_tool_row=api_tool_row,
    build_energy_circuit_loads_payload=build_energy_circuit_loads_payload,
    circuit_row_api=circuit_row_api,
    cumulative_energy_points=cumulative_energy_points,
    decimate_rows=decimate_rows,
    energy_elvia_control_module_payload=energy_elvia_control_module_payload,
    energy_elvia_module_payload=energy_elvia_module_payload,
    load_row_api=load_row_api,
    load_sunbed_power_analysis=load_sunbed_power_analysis,
    parse_day=parse_day,
)
from fibaro_core.services.modules import ventilation as ventilation_module
ventilation_module_dependencies = ventilation_module.Dependencies(
    VENT_TIMELINE_DEVICES=VENT_TIMELINE_DEVICES,
    api_config_field_rows=api_config_field_rows,
    api_config_history_rows=api_config_history_rows,
    api_filter=api_filter,
    api_filter_int=api_filter_int,
    api_filter_value=api_filter_value,
    api_pick=api_pick,
    api_rule_rows=api_rule_rows,
    api_tool_row=api_tool_row,
    build_temp_day=build_temp_day,
    clean_display_text=clean_display_text,
    config_rules=config_rules,
    display_action=display_action,
    display_control_mode=display_control_mode,
    empty_ventilation_day_payload=empty_ventilation_day_payload,
    fetch_rows=fetch_rows,
    get_or_create_config=get_or_create_config,
    hc3_fetch_switch_statuses=hc3_fetch_switch_statuses,
    hc3_switch_config_for_timeline_device=hc3_switch_config_for_timeline_device,
    merge_config_values=merge_config_values,
    parse_day=parse_day,
    percent_between=percent_between,
    ventilation_day_payload=ventilation_day_payload,
    ventilation_latest_payload=ventilation_latest_payload,
    ventilation_settings_payload=ventilation_settings_payload,
    ventilation_status_payload=ventilation_status_payload,
)
from fibaro_core.services.modules import lights as lights_module
lights_module_dependencies = lights_module.Dependencies(
    LIGHT_TIMELINE_DEVICES=LIGHT_TIMELINE_DEVICES,
    api_day_navigation=api_day_navigation,
    api_filter=api_filter,
    api_filter_int=api_filter_int,
    api_filter_value=api_filter_value,
    api_pick=api_pick,
    build_lux_day=build_lux_day,
    build_solar_elevation_samples=build_solar_elevation_samples,
    control_settings_payload=control_settings_payload,
    fetch_rows=fetch_rows,
    fetch_yr_cloud_samples=fetch_yr_cloud_samples,
    get_or_create_config=get_or_create_config,
    light_sample_state=light_sample_state,
    merge_config_values=merge_config_values,
    parse_day=parse_day,
)
from fibaro_core.services.modules import cleaning as cleaning_module
cleaning_module_dependencies = cleaning_module.Dependencies(
    DREAME_EXPECTED_ROBOT_NAME=DREAME_EXPECTED_ROBOT_NAME,
    api_pick=api_pick,
    api_roborock_active_cycle=api_roborock_active_cycle,
    api_tool_row=api_tool_row,
    config_defaults=config_defaults,
    latest_cleaning_robot_sample=latest_cleaning_robot_sample,
    merge_config_values=merge_config_values,
    roborock_water_interlock_from_sample=roborock_water_interlock_from_sample,
)
from fibaro_core.services.modules import maintenance as maintenance_module
maintenance_module_dependencies = maintenance_module.Dependencies(
    OWNTRACKS_SITE_VISIT_LOCATION_KEY=OWNTRACKS_SITE_VISIT_LOCATION_KEY,
    SITE_VISIT_ACTIVE_MAX_HOURS=SITE_VISIT_ACTIVE_MAX_HOURS,
    api_maintenance_log_edit=api_maintenance_log_edit,
    maintenance_log_row=maintenance_log_row,
    site_visit_is_current=site_visit_is_current,
    site_visit_is_stale=site_visit_is_stale,
    site_visit_label=site_visit_label,
    site_visit_row=site_visit_row,
)
from fibaro_core.services.modules import system as system_module
system_module_dependencies = system_module.Dependencies(
    ai_dataset_overview=ai_dataset_overview,
    api_access_key_edit=api_access_key_edit,
    api_access_key_row=api_access_key_row,
    api_admin_manual_payload=api_admin_manual_payload,
    api_config_value_rows=api_config_value_rows,
    api_import_status_rows=api_import_status_rows,
    api_pick=api_pick,
    api_tool_row=api_tool_row,
    build_admin_data_quality=build_admin_data_quality,
    build_admin_relation_analysis=build_admin_relation_analysis,
    build_admin_task_rows=build_admin_task_rows,
    build_reconciliation_control=build_reconciliation_control,
    effective_openai_settings=effective_openai_settings,
    import_status_rows=import_status_rows,
    row_to_dict=row_to_dict,
)
module_handlers = {
    "omsetning": partial(revenue_module.render, dependencies=revenue_module_dependencies),
    "parkering": partial(parking_module.render, dependencies=parking_module_dependencies),
    "soling": partial(sun_module.render, dependencies=sun_module_dependencies),
    "energi": partial(energy_module.render, dependencies=energy_module_dependencies),
    "ventilasjon": partial(ventilation_module.render, dependencies=ventilation_module_dependencies),
    "lys": partial(lights_module.render, dependencies=lights_module_dependencies),
    "renhold": partial(cleaning_module.render, dependencies=cleaning_module_dependencies),
    "vedlikehold": partial(maintenance_module.render, dependencies=maintenance_module_dependencies),
    "admin": partial(system_module.render, dependencies=system_module_dependencies),
    "koble": partial(linking_module.render, dependencies=linking_module_dependencies),
}
modules_http = modules_routes.create_router(modules_routes.Dependencies(async_session=async_session, handlers=module_handlers))
api_v2_module = modules_http.endpoints["api_v2_module"]
from fibaro_core.routers import linking_routes
linking_http = linking_routes.create_router(linking_routes.Dependencies(
    PARKING_SUN_LINK_CONFIRMED=PARKING_SUN_LINK_CONFIRMED,
    PARKING_SUN_LINK_REJECTED=PARKING_SUN_LINK_REJECTED,
    SUN2_AXIS_SNAPSHOT_TOLERANCE_SECONDS=SUN2_AXIS_SNAPSHOT_TOLERANCE_SECONDS,
    async_session=async_session,
    clear_summary_cache=clear_summary_cache,
    get_parking_sun_link_state=get_parking_sun_link_state,
    has_koble_worker_access=has_koble_worker_access,
    logger=logger,
    parking_sun_link_assessment=parking_sun_link_assessment,
    parking_sun_link_probability=parking_sun_link_probability,
    parking_sun_link_status_value=parking_sun_link_status_value,
    redirect_with_query_params=redirect_with_query_params,
    refresh_parking_sun_link_candidate_pairs=refresh_parking_sun_link_candidate_pairs,
    refresh_parking_sun_link_state_counts=refresh_parking_sun_link_state_counts,
    require_settings_access=require_settings_access,
    reset_parking_sun_link_data=reset_parking_sun_link_data,
    run_sun2_axis_snapshot_link_once=run_sun2_axis_snapshot_link_once,
    update_parking_sun_link_import_status=update_parking_sun_link_import_status,
))
api_v2_koble_candidate_update = linking_http.endpoints["api_v2_koble_candidate_update"]
api_v2_koble_restart = linking_http.endpoints["api_v2_koble_restart"]
api_v2_koble_settings_update = linking_http.endpoints["api_v2_koble_settings_update"]
api_v2_koble_start = linking_http.endpoints["api_v2_koble_start"]
api_v2_koble_stop = linking_http.endpoints["api_v2_koble_stop"]
api_v2_koble_worker_config = linking_http.endpoints["api_v2_koble_worker_config"]
api_v2_koble_worker_results = linking_http.endpoints["api_v2_koble_worker_results"]
api_v2_koble_worker_status = linking_http.endpoints["api_v2_koble_worker_status"]
sun2_sessions_link_images = linking_http.endpoints["sun2_sessions_link_images"]
from fibaro_core.routers import maintenance_routes
maintenance_http = maintenance_routes.create_router(maintenance_routes.Dependencies(
    MAINTENANCE_ACTION_OPTIONS=MAINTENANCE_ACTION_OPTIONS,
    MAINTENANCE_PRIORITY_OPTIONS=MAINTENANCE_PRIORITY_OPTIONS,
    MAINTENANCE_STATUS_OPTIONS=MAINTENANCE_STATUS_OPTIONS,
    MAINTENANCE_TARGET_OPTIONS=MAINTENANCE_TARGET_OPTIONS,
    OWNTRACKS_SITE_VISIT_LOCATION_KEY=OWNTRACKS_SITE_VISIT_LOCATION_KEY,
    api_maintenance_log_edit=api_maintenance_log_edit,
    async_session=async_session,
    clean_maintenance_option=clean_maintenance_option,
    find_site_visit_for_maintenance=find_site_visit_for_maintenance,
    logger=logger,
    maintenance_datetime_value=maintenance_datetime_value,
    maintenance_log_row=maintenance_log_row,
    maintenance_room_value=maintenance_room_value,
    maintenance_target_name=maintenance_target_name,
    normalize_maintenance_tags=normalize_maintenance_tags,
    require_settings_access=require_settings_access,
    run_owntracks_site_visit_sync=run_owntracks_site_visit_sync,
    site_visit_confidence_percent=site_visit_confidence_percent,
    site_visit_display_duration=site_visit_display_duration,
    site_visit_is_stale=site_visit_is_stale,
    site_visit_label=site_visit_label,
    site_visit_row=site_visit_row,
    site_visit_status_label=site_visit_status_label,
))
api_v2_maintenance_log_create = maintenance_http.endpoints["api_v2_maintenance_log_create"]
api_v2_maintenance_log_update = maintenance_http.endpoints["api_v2_maintenance_log_update"]
api_v2_maintenance_site_visit_detail = maintenance_http.endpoints["api_v2_maintenance_site_visit_detail"]
api_v2_maintenance_site_visit_update = maintenance_http.endpoints["api_v2_maintenance_site_visit_update"]
api_v2_maintenance_site_visits = maintenance_http.endpoints["api_v2_maintenance_site_visits"]
api_v2_maintenance_site_visits_sync = maintenance_http.endpoints["api_v2_maintenance_site_visits_sync"]
from fibaro_core.routers import cleaning_routes
cleaning_http = cleaning_routes.create_router(cleaning_routes.Dependencies(
    DREAME_CONTROL_TOKEN=DREAME_CONTROL_TOKEN,
    ROBOROCK_CONTROL_TOKEN=ROBOROCK_CONTROL_TOKEN,
    api_roborock_active_cycle=api_roborock_active_cycle,
    apply_roborock_cleaning_profile_values=apply_roborock_cleaning_profile_values,
    async_session=async_session,
    ensure_default_roborock_door_automation=ensure_default_roborock_door_automation,
    import_roborock_cleaning_zones=import_roborock_cleaning_zones,
    post_dreame_control=post_dreame_control,
    post_roborock_control=post_roborock_control,
    require_master=require_master,
    roborock_cleaning_profile_payload=roborock_cleaning_profile_payload,
    roborock_door_automation_payload=roborock_door_automation_payload,
    roborock_water_interlock_from_sample=roborock_water_interlock_from_sample,
    row_to_dict=row_to_dict,
    templates=templates,
))
api_cleaning_night_report = cleaning_http.endpoints["api_cleaning_night_report"]
api_cleaning_refill_log = cleaning_http.endpoints["api_cleaning_refill_log"]
api_cleaning_robot_control = cleaning_http.endpoints["api_cleaning_robot_control"]
api_cleaning_robot_detail = cleaning_http.endpoints["api_cleaning_robot_detail"]
api_cleaning_water_report = cleaning_http.endpoints["api_cleaning_water_report"]
api_cleaning_weekly_jobs = cleaning_http.endpoints["api_cleaning_weekly_jobs"]
api_create_roborock_cleaning_profile = cleaning_http.endpoints["api_create_roborock_cleaning_profile"]
api_delete_roborock_cleaning_profile = cleaning_http.endpoints["api_delete_roborock_cleaning_profile"]
api_import_roborock_cleaning_zones = cleaning_http.endpoints["api_import_roborock_cleaning_zones"]
api_reset_roborock_door_automation_counter = cleaning_http.endpoints["api_reset_roborock_door_automation_counter"]
api_update_roborock_cleaning_profile = cleaning_http.endpoints["api_update_roborock_cleaning_profile"]
api_update_roborock_door_automation = cleaning_http.endpoints["api_update_roborock_door_automation"]
classic_cleaning_json = cleaning_http.endpoints["classic_cleaning_json"]
classic_cleaning_overview = cleaning_http.endpoints["classic_cleaning_overview"]
classic_cleaning_robot_detail = cleaning_http.endpoints["classic_cleaning_robot_detail"]
cleaning_json = cleaning_http.endpoints["cleaning_json"]
cleaning_overview = cleaning_http.endpoints["cleaning_overview"]
cleaning_robot_detail = cleaning_http.endpoints["cleaning_robot_detail"]
from fibaro_core.routers import ingestion_routes
ingestion_http = ingestion_routes.create_router(ingestion_routes.Dependencies(
    api_import_job_run_row=api_import_job_run_row,
    api_import_status_row=api_import_status_row,
    api_import_status_rows=api_import_status_rows,
    async_session=async_session,
    clear_summary_cache=clear_summary_cache,
    door_event_from_payload=door_event_from_payload,
    generic_from_payload=generic_from_payload,
    import_job_definition=import_job_definition,
    import_status_rows=import_status_rows,
    ingest_roborock_robot=ingest_roborock_robot,
    ingest_roborock_telemetry_robot=ingest_roborock_telemetry_robot,
    ingest_sun2_beds=ingest_sun2_beds,
    ingest_sun2_finance_settlements=ingest_sun2_finance_settlements,
    ingest_sun2_members=ingest_sun2_members,
    ingest_sun2_product_sales=ingest_sun2_product_sales,
    ingest_sun2_room_stats=ingest_sun2_room_stats,
    ingest_sun2_tanning_sessions=ingest_sun2_tanning_sessions,
    json_safe_model_payload=json_safe_model_payload,
    light_from_payload=light_from_payload,
    light_ntfy_payload=light_ntfy_payload,
    light_sample_from_payload=light_sample_from_payload,
    met_weather_cached=met_weather_cached,
    payload_weather_symbol=payload_weather_symbol,
    payload_weather_text=payload_weather_text,
    record_import_job=record_import_job,
    save_record=save_record,
    save_yr_sample_for_payload=save_yr_sample_for_payload,
    schedule_sun2_axis_snapshot_link=schedule_sun2_axis_snapshot_link,
    sun2_duplicate_session_id_payload=sun2_duplicate_session_id_payload,
    upsert_energy_fibaro_sample=upsert_energy_fibaro_sample,
    upsert_kjeller_measurement_sample=upsert_kjeller_measurement_sample,
    vent_from_payload=vent_from_payload,
    vent_sample_from_payload=vent_sample_from_payload,
    ventilation_ntfy_payload=ventilation_ntfy_payload,
))
api_hc3_door_event = ingestion_http.endpoints["api_hc3_door_event"]
energy_fibaro_ingest = ingestion_http.endpoints["energy_fibaro_ingest"]
hc3_meter_reading_log = ingestion_http.endpoints["hc3_meter_reading_log"]
import_status_detail = ingestion_http.endpoints["import_status_detail"]
import_status_json = ingestion_http.endpoints["import_status_json"]
import_status_report = ingestion_http.endpoints["import_status_report"]
legacy_log_data = ingestion_http.endpoints["legacy_log_data"]
log_event = ingestion_http.endpoints["log_event"]
roborock_ingest = ingestion_http.endpoints["roborock_ingest"]
roborock_telemetry_ingest = ingestion_http.endpoints["roborock_telemetry_ingest"]
sun2_beds_ingest = ingestion_http.endpoints["sun2_beds_ingest"]
sun2_finance_settlements_ingest = ingestion_http.endpoints["sun2_finance_settlements_ingest"]
sun2_members_ingest = ingestion_http.endpoints["sun2_members_ingest"]
sun2_product_sales_ingest = ingestion_http.endpoints["sun2_product_sales_ingest"]
sun2_room_stats_ingest = ingestion_http.endpoints["sun2_room_stats_ingest"]
sun2_sessions_ingest = ingestion_http.endpoints["sun2_sessions_ingest"]

control_http.register_endpoint(app, "api_unifi_protect_status")
control_http.register_endpoint(app, "api_unifi_protect_cameras")
control_http.register_endpoint(app, "api_unifi_protect_capabilities")
control_http.register_endpoint(app, "api_unifi_protect_stats")
control_http.register_endpoint(app, "api_unifi_protect_events")
control_http.register_endpoint(app, "api_unifi_protect_recognitions")
control_http.register_endpoint(app, "api_unifi_protect_recognition_detail")
control_http.register_endpoint(app, "api_unifi_protect_daily_license_plates")
parking_http.register_endpoint(app, "api_parking_control_report")
control_http.register_endpoint(app, "api_unifi_protect_bollards")
control_http.register_endpoint(app, "api_unifi_protect_bollard_mobile_notifications")
control_http.register_endpoint(app, "api_test_unifi_protect_bollard_mobile_notification")
parking_http.register_endpoint(app, "api_cars_day")
parking_http.register_endpoint(app, "api_cars_day_detections")
control_http.register_endpoint(app, "api_unifi_protect_snapshot")
control_http.register_endpoint(app, "api_unifi_protect_recognition_snapshot")
control_http.register_endpoint(app, "api_unifi_protect_bollard_baseline")
control_http.register_endpoint(app, "api_unifi_protect_bollard_camera_image")
control_http.register_endpoint(app, "api_unifi_protect_bollard_camera_crop")
control_http.register_endpoint(app, "api_unifi_protect_bollard_asset_image")
control_http.register_endpoint(app, "api_unifi_protect_bollard_incident_image")
system_http.register_endpoint(app, "health")
system_http.register_endpoint(app, "favicon")
access_http.register_endpoint(app, "login_view")
access_http.register_endpoint(app, "login_submit")
access_http.register_endpoint(app, "logout")
access_http.register_endpoint(app, "api_auth_session_create")
access_http.register_endpoint(app, "api_auth_session_delete")
access_http.register_endpoint(app, "api_auth_me")
system_http.register_endpoint(app, "api_admin_builds")
system_http.register_endpoint(app, "api_manual")
system_http.register_endpoint(app, "api_admin_manual")
system_http.register_endpoint(app, "api_system_notifications")
system_http.register_endpoint(app, "api_system_incident_review")
app.include_router(create_assets_router(async_session, require_settings_access))
app.include_router(create_automations_router(async_session, require_settings_access))
system_http.register_endpoint(app, "api_system_search")
system_http.register_endpoint(app, "api_system_subsystems")
system_http.register_endpoint(app, "api_admin_build")
system_http.register_endpoint(app, "ai_redirect")
building_http.register_endpoint(app, "lights_redirect")
building_http.register_endpoint(app, "ventilation_redirect")
system_http.register_endpoint(app, "ai_search_view")
system_http.register_endpoint(app, "ai_search_submit")
system_http.register_endpoint(app, "ai_settings_view")
system_http.register_endpoint(app, "ai_settings_update")
system_http.register_endpoint(app, "ai_datasets_json")
system_http.register_endpoint(app, "ai_logs_json")
system_http.register_endpoint(app, "account_view")
system_http.register_endpoint(app, "account_build_view")
system_http.register_endpoint(app, "account_technical_view")
system_http.register_endpoint(app, "account_manual_view")
energy_http.register_endpoint(app, "energy_view")
access_http.register_endpoint(app, "keys_view")
access_http.register_endpoint(app, "keys_create")
access_http.register_endpoint(app, "keys_disable")
access_http.register_endpoint(app, "keys_enable")
access_http.register_endpoint(app, "keys_role_update")
building_http.register_endpoint(app, "api_control_configs")
building_http.register_endpoint(app, "api_control_config")
building_http.register_endpoint(app, "api_control_config_update")
system_http.register_endpoint(app, "root_service_info")
system_http.register_endpoint(app, "api_mobile_preview_screens")
system_http.register_endpoint(app, "api_mobile_preview_frame")
sun_http.register_endpoint(app, "sun2_session_image")
sun_http.register_endpoint(app, "sun2_session_image_item")
sun_http.register_endpoint(app, "api_sun2_axis_snapshot_image")
sun_http.register_endpoint(app, "api_sun2_session_image_browser")
sun_http.register_endpoint(app, "api_sun2_session_select_image")
sun_http.register_endpoint(app, "api_sun2_session_set_primary_image")
revenue_http.register_endpoint(app, "index")
revenue_http.register_endpoint(app, "status_key_metrics_view")
revenue_http.register_endpoint(app, "api_v2_status_comparison")
sun_http.register_endpoint(app, "api_v2_sun2_year_comparison")
parking_http.register_endpoint(app, "api_v2_parking_year_comparison")
parking_http.register_endpoint(app, "api_v2_parking_time_distribution")
parking_http.register_endpoint(app, "api_v2_parking_weekly_averages")
parking_http.register_endpoint(app, "api_v2_parking_weekly_average_years")
revenue_http.register_endpoint(app, "api_v2_revenue_year_comparison")
revenue_http.register_endpoint(app, "api_operations_overview")
revenue_http.register_endpoint(app, "api_v2_overview")
revenue_http.register_endpoint(app, "api_v2_revenue_month")
revenue_http.register_endpoint(app, "api_v2_settlement_detail")
revenue_http.register_endpoint(app, "api_v2_settlement_attachment")
sun_http.register_endpoint(app, "api_v2_sun_settlement_detail")
sun_http.register_endpoint(app, "api_v2_sun_settlement_attachment")
modules_http.register_endpoint(app, "api_v2_module")
parking_http.register_endpoint(app, "api_v2_parking_vehicle_detail")
sun_http.register_endpoint(app, "api_v2_sun2_save_forecast")
sun_http.register_endpoint(app, "api_v2_upload_sun_settlement")
parking_http.register_endpoint(app, "api_v2_fetch_parking_settlements")
parking_http.register_endpoint(app, "api_v2_parking_save_forecast")
parking_http.register_endpoint(app, "api_v2_parking_refresh")
parking_http.register_endpoint(app, "api_v2_parking_svv_sync")
parking_http.register_endpoint(app, "api_v2_parking_car_info_sync")
parking_http.register_endpoint(app, "api_v2_parking_clear_area_not_found")
parking_http.register_endpoint(app, "api_v2_parking_vehicle_clear_not_found")
linking_http.register_endpoint(app, "api_v2_koble_start")
linking_http.register_endpoint(app, "api_v2_koble_stop")
linking_http.register_endpoint(app, "api_v2_koble_restart")
linking_http.register_endpoint(app, "api_v2_koble_settings_update")
linking_http.register_endpoint(app, "api_v2_koble_candidate_update")
linking_http.register_endpoint(app, "api_v2_koble_worker_config")
linking_http.register_endpoint(app, "api_v2_koble_worker_status")
linking_http.register_endpoint(app, "api_v2_koble_worker_results")
energy_http.register_endpoint(app, "api_v2_energy_circuit_update")
energy_http.register_endpoint(app, "api_v2_energy_node_create")
energy_http.register_endpoint(app, "api_v2_energy_node_update")
energy_http.register_endpoint(app, "api_v2_energy_hc3_devices")
energy_http.register_endpoint(app, "api_v2_energy_nodes_live")
energy_http.register_endpoint(app, "api_v2_energy_load_create")
energy_http.register_endpoint(app, "api_v2_energy_load_update")
maintenance_http.register_endpoint(app, "api_v2_maintenance_log_create")
maintenance_http.register_endpoint(app, "api_v2_maintenance_log_update")
maintenance_http.register_endpoint(app, "api_v2_maintenance_site_visit_detail")
maintenance_http.register_endpoint(app, "api_v2_maintenance_site_visit_update")
maintenance_http.register_endpoint(app, "api_v2_maintenance_site_visits")
maintenance_http.register_endpoint(app, "api_v2_maintenance_site_visits_sync")
access_http.register_endpoint(app, "api_v2_admin_user_create")
access_http.register_endpoint(app, "api_v2_admin_user_update")
revenue_http.register_endpoint(app, "status_revenue_month_view")
revenue_http.register_endpoint(app, "status_statistics_view")
revenue_http.register_endpoint(app, "import_status_view")
revenue_http.register_endpoint(app, "day_view")
building_http.register_endpoint(app, "day_lux_view")
building_http.register_endpoint(app, "day_temp_view")
ingestion_http.register_endpoint(app, "legacy_log_data")
ingestion_http.register_endpoint(app, "hc3_meter_reading_log")
ingestion_http.register_endpoint(app, "log_event")
ingestion_http.register_endpoint(app, "api_hc3_door_event")
control_http.register_endpoint(app, "api_hc3_doors_poll_sync")
ingestion_http.register_endpoint(app, "import_status_report")
ingestion_http.register_endpoint(app, "import_status_json")
ingestion_http.register_endpoint(app, "import_status_detail")
ingestion_http.register_endpoint(app, "roborock_ingest")
ingestion_http.register_endpoint(app, "roborock_telemetry_ingest")
ingestion_http.register_endpoint(app, "sun2_room_stats_ingest")
ingestion_http.register_endpoint(app, "sun2_sessions_ingest")
ingestion_http.register_endpoint(app, "sun2_beds_ingest")
ingestion_http.register_endpoint(app, "sun2_members_ingest")
ingestion_http.register_endpoint(app, "sun2_product_sales_ingest")
ingestion_http.register_endpoint(app, "sun2_finance_settlements_ingest")
sun_http.register_endpoint(app, "sun2_backfill_room_identity")
sun_http.register_endpoint(app, "sun2_room_stats_legacy_redirect")
sun_http.register_endpoint(app, "sun2_room_stats_json_legacy_redirect")
parking_http.register_endpoint(app, "parking_redirect")
parking_http.register_endpoint(app, "parking_easypark_import_csv")
parking_http.register_endpoint(app, "parking_vehicle_svv_sync_api")
parking_http.register_endpoint(app, "parking_refresh")
parking_http.register_endpoint(app, "parking_overview_view")
parking_http.register_endpoint(app, "parking_statistics_view")
parking_http.register_endpoint(app, "parking_forecast_view")
parking_http.register_endpoint(app, "parking_forecast_save")
parking_http.register_endpoint(app, "parking_vehicle_statistics_view")
parking_http.register_endpoint(app, "parking_area_overview_view")
parking_http.register_endpoint(app, "parking_sessions_view")
parking_http.register_endpoint(app, "parking_vehicles_view")
parking_http.register_endpoint(app, "parking_vehicle_clear_not_found_area")
parking_http.register_endpoint(app, "parking_name_lookup_view")
parking_http.register_endpoint(app, "parking_area_lookup_view")
parking_http.register_endpoint(app, "parking_car_info_candidates_api")
parking_http.register_endpoint(app, "parking_missing_names_api")
parking_http.register_endpoint(app, "parking_missing_areas_api")
parking_http.register_endpoint(app, "parking_vehicle_name_api")
parking_http.register_endpoint(app, "parking_vehicle_area_api")
parking_http.register_endpoint(app, "parking_vehicle_car_info_api")
parking_http.register_endpoint(app, "parking_vehicle_detail_view")
parking_http.register_endpoint(app, "parking_vehicle_detail_save")
energy_http.register_endpoint(app, "energy_redirect")
energy_http.register_endpoint(app, "energy_overview_legacy_redirect")
sun_http.register_endpoint(app, "energy_soling_legacy_redirect")
ingestion_http.register_endpoint(app, "energy_fibaro_ingest")
energy_http.register_endpoint(app, "api_energy_elvia_upload")
energy_http.register_endpoint(app, "energy_status_view")
energy_http.register_endpoint(app, "energy_circuits_view")
energy_http.register_endpoint(app, "energy_circuit_save")
energy_http.register_endpoint(app, "energy_circuits_pdf")
energy_http.register_endpoint(app, "energy_loads_view")
energy_http.register_endpoint(app, "energy_loads_pdf")
energy_http.register_endpoint(app, "energy_load_save")
energy_http.register_endpoint(app, "energy_load_toggle_active")
energy_http.register_endpoint(app, "energy_fibaro_json")
energy_http.register_endpoint(app, "energy_sunbed_consumption_view")
sun_http.register_endpoint(app, "sun2_redirect")
sun_http.register_endpoint(app, "sun2_overview_view")
sun_http.register_endpoint(app, "sun2_forecast_view")
sun_http.register_endpoint(app, "sun2_forecast_save")
sun_http.register_endpoint(app, "sun2_room_stats_view")
sun_http.register_endpoint(app, "sun2_sessions_view")
linking_http.register_endpoint(app, "sun2_sessions_link_images")
sun_http.register_endpoint(app, "api_v2_sun2_link_snapshot_images")
sun_http.register_endpoint(app, "sun2_day_timeline_view")
sun_http.register_endpoint(app, "sun2_beds_view")
sun_http.register_endpoint(app, "sun2_members_view")
sun_http.register_endpoint(app, "sun2_room_stats_json")
sun_http.register_endpoint(app, "sun2_beds_json")
sun_http.register_endpoint(app, "sun2_members_json")
sun_http.register_endpoint(app, "sun2_sessions_json")
energy_http.register_endpoint(app, "energy_elvia_view")
energy_http.register_endpoint(app, "energy_elvia_upload")
energy_http.register_endpoint(app, "energy_elvia_json")
cleaning_http.register_endpoint(app, "cleaning_overview")
cleaning_http.register_endpoint(app, "api_cleaning_night_report")
cleaning_http.register_endpoint(app, "api_cleaning_weekly_jobs")
cleaning_http.register_endpoint(app, "api_cleaning_water_report")
cleaning_http.register_endpoint(app, "api_cleaning_refill_log")
cleaning_http.register_endpoint(app, "api_cleaning_robot_detail")
cleaning_http.register_endpoint(app, "api_update_roborock_door_automation")
cleaning_http.register_endpoint(app, "api_reset_roborock_door_automation_counter")
cleaning_http.register_endpoint(app, "api_import_roborock_cleaning_zones")
cleaning_http.register_endpoint(app, "api_create_roborock_cleaning_profile")
cleaning_http.register_endpoint(app, "api_update_roborock_cleaning_profile")
cleaning_http.register_endpoint(app, "api_delete_roborock_cleaning_profile")
cleaning_http.register_endpoint(app, "api_cleaning_robot_control")
cleaning_http.register_endpoint(app, "cleaning_robot_detail")
cleaning_http.register_endpoint(app, "cleaning_json")
building_http.register_endpoint(app, "lights_view")
building_http.register_endpoint(app, "lights_json")
building_http.register_endpoint(app, "lights_download")
building_http.register_endpoint(app, "light_samples_json")
building_http.register_endpoint(app, "light_samples_view")
building_http.register_endpoint(app, "light_samples_download")
building_http.register_endpoint(app, "ventilation_view")
building_http.register_endpoint(app, "ventilation_json")
building_http.register_endpoint(app, "ventilation_download")
building_http.register_endpoint(app, "ventilation_samples_view")
building_http.register_endpoint(app, "ventilation_samples_json")
building_http.register_endpoint(app, "ventilation_samples_download")
building_http.register_endpoint(app, "yr_samples_view")
building_http.register_endpoint(app, "yr_samples_json")
building_http.register_endpoint(app, "yr_samples_download")
system_http.register_endpoint(app, "generic_download")
system_http.register_endpoint(app, "events_json")
control_http.register_endpoint(app, "api_hc3_door_events_json")
control_http.register_endpoint(app, "api_hc3_doors_status")
control_http.register_endpoint(app, "api_hc3_doors_sunroom_sessions")
control_http.register_endpoint(app, "api_hc3_doors_sunroom_logic")
control_http.register_endpoint(app, "api_hc3_doors_alarm")
control_http.register_endpoint(app, "api_hc3_doors_sunroom_overview")
control_http.register_endpoint(app, "api_hc3_doors_sunroom_room_detail")
parking_http.register_endpoint(app, "classic_parking_vehicles_view")
parking_http.register_endpoint(app, "classic_parking_name_lookup_view")
parking_http.register_endpoint(app, "classic_parking_area_lookup_view")
parking_http.register_endpoint(app, "classic_parking_vehicle_detail_view")
energy_http.register_endpoint(app, "classic_energy_circuits_pdf")
energy_http.register_endpoint(app, "classic_energy_loads_pdf")
building_http.register_endpoint(app, "classic_light_settings_view")
cleaning_http.register_endpoint(app, "classic_cleaning_overview")
cleaning_http.register_endpoint(app, "classic_cleaning_robot_detail")
cleaning_http.register_endpoint(app, "classic_cleaning_json")
