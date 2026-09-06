"""Synthetic database tests: no collectors, network requests or production writes."""

import asyncio
from dataclasses import replace
from datetime import date, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from starlette.requests import Request

import main
from fibaro_core.models import (
    AccessLog, EnergyFibaroSample, EnergyHourlyConsumption, MaintenanceLogEntry,
    ParkingSunLinkCandidate, ParkingSunLinkJobState, ParkingSunLinkMatch,
    ParkingSunLinkProcessed, ParkingVehicle, SiteVisit,
)
from fibaro_core.schemas import ParkingSunLinkCandidateUpdate
from fibaro_core.services.bollard_health import bollard_collection_issues
from fibaro_core.services.modules import linking, maintenance


class AsyncTestSession:
    def __init__(self, session):
        self.session = session

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        pass

    async def execute(self, query):
        return self.session.execute(query)

    async def get(self, *args, **kwargs):
        return self.session.get(*args, **kwargs)

    async def commit(self):
        self.session.commit()

    def add(self, value):
        self.session.add(value)


@pytest.fixture
def database():
    engine = create_engine('sqlite://')
    for model in (SiteVisit, MaintenanceLogEntry, EnergyFibaroSample, EnergyHourlyConsumption,
                  ParkingSunLinkCandidate, ParkingSunLinkMatch, ParkingSunLinkProcessed, ParkingVehicle, AccessLog):
        model.__table__.create(engine)
    with Session(engine, expire_on_commit=False) as session:
        yield session, AsyncTestSession(session)
    engine.dispose()


def request(query=b''):
    return Request({'type': 'http', 'method': 'GET', 'path': '/', 'query_string': query, 'headers': [], 'state': {'auth_username': 'test'}})


def test_all_open_maintenance_and_month_totals_survive_history_limit(database):
    session, remote = database
    session.add(MaintenanceLogEntry(id=1, performed_at=datetime(2025, 1, 1), summary='Old open item', follow_up_needed=True, status='Åpen'))
    session.add(MaintenanceLogEntry(id=2, performed_at=datetime(2025, 1, 1), summary='Closed item', follow_up_needed=True, status=' LUKKET '))
    session.add_all(MaintenanceLogEntry(id=i + 10, performed_at=datetime(2026, 9, 6, 10) + timedelta(seconds=i), summary='Synthetic', target_type='seng') for i in range(350))
    session.commit()
    result = asyncio.run(maintenance.render(remote, request(), 'vedlikehold', 'oversikt', None, None, datetime(2026, 9, 6, 20), main.maintenance_module_dependencies))
    cards = {row['title']: row for row in result['cards']}
    assert cards['Må følges opp']['value'] == '1'
    assert cards['I dag']['value'] == '350'
    assert cards['Denne måneden']['value'] == '350'
    assert [row['id'] for row in result['tables'][0]['rows']] == [1]
    assert len(result['tables'][1]['rows']) == 300


def elvia(hour, amount=1):
    return EnergyHourlyConsumption(meter_id='test', measured_at=datetime(2026, 9, 5, hour), stat_date=date(2026, 9, 5), year=2026, month=9, day=5, hour=hour, consumption_kwh=amount, status='OK')


def energy_result(remote):
    return asyncio.run(main.energy_elvia_control_module_payload(remote, date(2026, 9, 5), date(2026, 9, 6)))


def test_missing_hc3_is_unknown_not_zero_and_no_comparison(database):
    session, remote = database
    session.add(elvia(0))
    session.commit()
    result = energy_result(remote)
    row = result['tables'][0]['rows'][0]
    assert row['hc3_kwh'] is None and row['diff_kwh'] is None and row['diff_percent'] is None
    cards = {row['title']: row for row in result['cards']}
    assert cards['Status']['value'] == 'Mangler HC3'
    assert cards['HC3 valgt dag']['value'] == '-'
    assert cards['Avvik i felles timer']['value'] == '-'


def test_energy_compares_only_shared_hours_and_keeps_true_zero(database):
    session, remote = database
    session.add_all([elvia(0, 0), elvia(1, 100)])
    session.add(EnergyFibaroSample(bucket_start=datetime(2026, 9, 5, 0), inntak_delta_kwh=0))
    session.add(EnergyFibaroSample(bucket_start=datetime(2026, 9, 5, 2), inntak_delta_kwh=10))
    session.commit()
    result = energy_result(remote)
    rows = result['tables'][0]['rows']
    assert rows[0]['hc3_kwh'] == 0 and rows[0]['diff_kwh'] == 0
    assert rows[1]['diff_kwh'] is None and rows[2]['diff_kwh'] is None
    cards = {row['title']: row for row in result['cards']}
    assert cards['Status']['value'] == 'Delvis grunnlag'
    assert float(cards['Avvik i felles timer']['value'].replace(',', '.')) == 0
    assert result['charts'][0]['metrics'][1]['series'][0]['data'][2] is None


def test_complete_energy_day_can_be_ok(database):
    session, remote = database
    session.add_all(elvia(hour, 0) for hour in range(24))
    session.add_all(EnergyFibaroSample(bucket_start=datetime(2026, 9, 5) + timedelta(seconds=30 * i), inntak_delta_kwh=0) for i in range(2880))
    session.commit()
    result = energy_result(remote)
    assert next(row['value'] for row in result['cards'] if row['title'] == 'Status') == 'OK'


@pytest.mark.parametrize('change', ['old', 'error', 'stopped', 'disabled', 'cameras', 'missing', 'invalid', 'future'])
def test_bollard_health_never_hides_missing_or_contradictory_evidence(change):
    payload = {'runtime': {'running': True, 'last_success_at': '2026-09-06T10:00:00Z'}, 'settings': {'monitoring_enabled': True, 'analysis_interval_seconds': 300}, 'summary': {'target_cameras': 3, 'connected_cameras': 3}}
    now = datetime(2026, 9, 6, 12, 5)
    assert bollard_collection_issues(payload, now)[0] == []
    if change == 'old': now += timedelta(hours=1)
    if change == 'error': payload['runtime']['last_error'] = 'Timeout'
    if change == 'stopped': payload['runtime']['running'] = False
    if change == 'disabled': payload['settings']['monitoring_enabled'] = False
    if change == 'cameras': payload['summary']['connected_cameras'] = 0
    if change == 'missing': payload['runtime'].pop('last_success_at')
    if change == 'invalid': payload['runtime']['last_success_at'] = 'invalid'
    if change == 'future': payload['runtime']['last_success_at'] = '2026-09-07T10:00:00Z'
    assert bollard_collection_issues(payload, now)[0]


@pytest.mark.parametrize(('modified', 'sun2', 'revoke', 'expected'), [(False, '123', True, None), (True, '123', True, '123'), (False, '456', True, '456'), (False, '123', False, '123')])
def test_reject_only_removes_explicitly_revoked_unchanged_link(database, modified, sun2, revoke, expected):
    session, remote = database
    stamp = datetime(2026, 9, 1, 10)
    candidate = ParkingSunLinkCandidate(id=1, generation=1, plate='TEST1', sun2_id='123', status='Bekreftet', confirmed_at=stamp, confirmed_by='test')
    vehicle = ParkingVehicle(plate='TEST1', sun2_id=sun2, updated_at=stamp + timedelta(minutes=int(modified)))
    session.add_all([candidate, vehicle])
    session.commit()
    deps = main.linking_http.dependencies
    with patch.object(deps, 'async_session', return_value=remote), patch.object(deps, 'require_settings_access', return_value=None), patch.object(deps, 'get_parking_sun_link_state', new=AsyncMock(return_value=SimpleNamespace(min_matches=2))), patch.object(deps, 'clear_summary_cache'):
        asyncio.run(main.api_v2_koble_candidate_update(request(), 1, ParkingSunLinkCandidateUpdate(status='Avvist', revoke_vehicle_link=revoke)))
    assert vehicle.sun2_id == expected
    assert candidate.status == 'Avvist' and candidate.rejected_by == 'test'
    assert candidate.confirmed_at == stamp
    assert session.scalar(select(AccessLog)).reason.startswith('Bekreftet->Avvist')


@pytest.mark.parametrize('view', ['biltreff', 'sun2', 'kandidater'])
def test_link_pages_include_pairs_after_250_with_stable_order(database, view):
    session, remote = database
    session.add_all(ParkingSunLinkCandidate(id=i, generation=1, plate=f'TEST{i}', sun2_id=str(i), parking_match_count=2, matches_count=2, status='Avventer') for i in range(1, 302))
    session.add(ParkingSunLinkCandidate(id=999, generation=1, plate='ONE', sun2_id='999', parking_match_count=1))
    session.commit()
    state = ParkingSunLinkJobState(generation=1, min_matches=2, max_minutes=3, enabled=False)
    deps = replace(main.linking_module_dependencies, get_parking_sun_link_state=AsyncMock(return_value=state), refresh_parking_sun_link_state_counts=AsyncMock(), parking_sun_link_matched_paid_totals=AsyncMock(return_value={}), parking_sun_link_qualified_distinct_matched_paid_total=AsyncMock(return_value=0))
    seen = []
    for page in range(1, 14):
        result = asyncio.run(linking.render(remote, request(f'limit=25&page={page}'.encode()), 'koble', view, None, None, datetime(2026, 9, 6), deps))['kobleReview']
        assert result['pageInfo']['totalRows'] == 301
        rows = result[{'biltreff': 'qualifiedRows', 'sun2': 'qualifiedSun2Rows', 'kandidater': 'candidates'}[view]]
        seen.extend(row['id'] for row in rows)
    assert len(seen) == len(set(seen)) == 301 and 999 not in seen


@pytest.mark.parametrize(('start', 'end', 'fee', 'excluded'), [
    (datetime(2026, 9, 1, 10), None, 50, False),
    (datetime(2026, 9, 6, 10), None, 50, True),
    (datetime(2026, 9, 5, 22), datetime(2026, 9, 6, 1), 50, True),
    (datetime(2026, 9, 5, 10), datetime(2026, 9, 5, 11), 50, False),
    (datetime(2026, 9, 6, 10), None, 0, False),
])
def test_old_open_parking_does_not_cover_future_observations(start, end, fee, excluded):
    parking = SimpleNamespace(start_time=start, end_time=end, fee_inc_vat=fee, car_license_number='TEST1')
    remote = AsyncMock()
    remote.__aenter__.return_value = remote
    from unittest.mock import MagicMock
    first = MagicMock()
    first.scalars.return_value.all.return_value = [parking]
    second = MagicMock()
    second.all.return_value = []
    remote.execute.side_effect = [first, second]
    source = {'days': [{'date': '2026-09-06', 'vehicles': [{'plate': 'TEST1', 'duration_minutes': 20, 'observation_count': 2}]}]}
    with patch.object(main.parking_dependencies, 'async_session', return_value=remote):
        result = asyncio.run(main.unpaid_registered_vehicle_stays_payload(source, date(2026, 9, 6), date(2026, 9, 7)))
    assert (len(result['days']) == 0) is excluded


def test_each_candidate_keeps_its_own_evidence_even_with_busy_neighbour(database):
    session, remote = database
    session.add_all(ParkingSunLinkCandidate(id=i, generation=1, plate=f'TEST{i}', sun2_id=str(i), parking_match_count=2, matches_count=2) for i in [1, 2])
    for i in range(402):
        pair = 2 if i < 2 else 1
        stamp = datetime(2026, 8, 1) + timedelta(minutes=10 * i)
        session.add(ParkingSunLinkMatch(id=i + 1, generation=1, plate=f'TEST{pair}', sun2_id=str(pair),
                                       parking_record_id=i + 1, sun_session_id=i + 1,
                                       parking_start_at=stamp, sun_started_at=stamp + timedelta(minutes=1)))
    session.commit()
    state = ParkingSunLinkJobState(generation=1, min_matches=2, max_minutes=3, enabled=False)
    deps = replace(main.linking_module_dependencies, get_parking_sun_link_state=AsyncMock(return_value=state),
                   refresh_parking_sun_link_state_counts=AsyncMock(), parking_sun_link_matched_paid_totals=AsyncMock(return_value={}),
                   parking_sun_link_qualified_distinct_matched_paid_total=AsyncMock(return_value=0))
    result = asyncio.run(linking.render(remote, request(b'limit=25'), 'koble', 'kandidater', None, None, datetime(2026, 9, 6), deps))
    assert {row['plate']: len(row['matches']) for row in result['kobleReview']['candidates']} == {'TEST1': 6, 'TEST2': 2}
