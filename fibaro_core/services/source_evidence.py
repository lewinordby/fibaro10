"""Read-only evidence, separate from successful imports and service liveness."""
from datetime import timedelta

from sqlalchemy import select

from fibaro_core.models import (
    DoorEvent, EnergyFibaroSample, EnergyHourlyConsumption, OutdoorLightSample,
    ParkingSession, RoborockRobot, Sun2TanningSession, VentilationSample,
)
from import_jobs import IMPORT_JOB_DEFINITIONS
from time_formatting import api_local_iso, local_now_naive, normalize_local_naive


# Event time is not a collection watermark. Only periodic measurements have
# an age threshold; a quiet car park/room is not a failed import.
SOURCE_MEASUREMENTS = {
    'hc3_energy_1min': (EnergyFibaroSample.bucket_start, 'Siste effektmåling', True),
    'hc3_light_5min': (OutdoorLightSample.timestamp, 'Siste luxmåling', True),
    'hc3_ventilation_5min': (VentilationSample.timestamp, 'Siste temperaturmåling', True),
    'hc3_door_events': (DoorEvent.timestamp, 'Siste dørhendelse', False),
    'sun2_sessions_import': (Sun2TanningSession.started_at, 'Siste registrerte soltime', False),
    'easypark_parking_import': (ParkingSession.start_time, 'Siste registrerte parkeringsstart', False),
    'elvia_monthly_import': (EnergyHourlyConsumption.measured_at, 'Siste forbrukstime', False),
}


def measurement_evidence(stamp, *, label, periodic=False, warning_minutes=None, now=None):
    now = normalize_local_naive(now) or local_now_naive()
    stamp = normalize_local_naive(stamp)
    status, status_text = 'unknown', 'Ingen måling registrert'
    if stamp:
        if stamp > now + timedelta(minutes=2):
            status, status_text = 'warn', 'Tidspunkt ligger i fremtiden'
        elif periodic and warning_minutes and now - stamp > timedelta(minutes=warning_minutes):
            status, status_text = 'warn', 'Målingen er eldre enn varselgrensen'
        else:
            status, status_text = 'ok' if periodic else 'observed', 'Måling registrert' if periodic else 'Hendelse registrert'
    return {'label': label, 'timestamp': api_local_iso(stamp), 'status': status, 'statusText': status_text,
            'periodic': periodic, 'warningMinutes': warning_minutes if periodic else None}


async def source_data_evidence(session, job_name):
    definition = IMPORT_JOB_DEFINITIONS[job_name]
    warning = definition.get('warning_after_minutes')
    measurements = []
    if job_name in SOURCE_MEASUREMENTS:
        column, label, periodic = SOURCE_MEASUREMENTS[job_name]
        stamp = (await session.execute(select(column).where(column.is_not(None)).order_by(column.desc()).limit(1))).scalar_one_or_none()
        measurements.append(measurement_evidence(stamp, label=label, periodic=periodic, warning_minutes=warning))
    elif job_name in ('roborock_sync', 'dreame_sync'):
        provider = job_name.removesuffix('_sync')
        robots = (await session.execute(select(RoborockRobot.name, RoborockRobot.last_status_at)
                    .where(RoborockRobot.provider == provider, RoborockRobot.integration_status == 'active')
                    .order_by(RoborockRobot.name))).all()
        measurements = [measurement_evidence(stamp, label=name, periodic=True, warning_minutes=warning)
                        for name, stamp in robots]
    return {
        'measurements': measurements,
        'coverageThrough': None,
        'coverageText': 'Kilden rapporterer ikke et eget, bekreftet tidspunkt for komplett datadekning.',
        'serviceHealth': 'not_checked',
        'serviceHealthText': 'Importstatus er ikke en helsesjekk av tjenesten.',
    }
