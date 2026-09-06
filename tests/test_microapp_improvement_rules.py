from datetime import date, datetime, timedelta
from types import SimpleNamespace

import pytest

from fibaro_core.services.cleaning_preparation import night_preparation
from fibaro_core.services.energy_quality import local_hour_occurrences, valid_consumption
from fibaro_core.services.parking_coverage import observed_payment_coverage
from fibaro_core.services.revenue_coverage import month_source_coverage


@pytest.mark.parametrize(('day', 'count', 'hour_two'), [
    (date(2026, 3, 29), 23, 0), (date(2026, 10, 25), 25, 2), (date(2026, 9, 6), 24, 1),
])
def test_actual_local_day_length(day, count, hour_two):
    hours = local_hour_occurrences(day)
    assert sum(hours.values()) == count
    assert hours.get(2, 0) == hour_two


@pytest.mark.parametrize('value', [None, 'invalid', -1, float('nan'), float('inf')])
def test_invalid_energy_is_not_zero(value):
    assert valid_consumption(value) is None


def test_valid_energy_includes_zero():
    assert valid_consumption(0) == 0
    assert valid_consumption('1.5') == 1.5


FIRST = datetime(2026, 9, 6, 10)
LAST = FIRST + timedelta(minutes=20)


def parking(start=0, end=20, amount=50):
    return SimpleNamespace(id=1, start_time=FIRST + timedelta(minutes=start),
                           end_time=None if end is None else FIRST + timedelta(minutes=end), fee_inc_vat=amount)


@pytest.mark.parametrize(('payments', 'cutoff', 'status', 'minutes'), [
    ([parking()], None, 'covered', 20),
    ([parking(0, 10), parking(5, 20)], LAST, 'covered', 20),
    ([parking(0, 5), parking(15, 20)], LAST, 'partial', 10),
    ([parking(0, 10)], FIRST, 'pending', 10),
    ([parking(0, None)], LAST, 'unknown', 0),
    ([parking(-1440, None)], LAST, 'unmatched', 0),
    ([parking(60, 80)], LAST, 'unmatched', 0),
    ([parking(amount=0)], LAST, 'unmatched', 0),
    ([], None, 'pending', 0),
    ([], LAST, 'unmatched', 0),
])
def test_payment_coverage_is_interval_based_and_conservative(payments, cutoff, status, minutes):
    result = observed_payment_coverage(FIRST, LAST, payments, cutoff)
    assert result['status'] == status
    assert result['coveredMinutes'] == minutes
    assert result['uncoveredMinutes'] == 20 - minutes


def test_timezone_and_invalid_observation_times():
    result = observed_payment_coverage('2026-09-06T08:00:00Z', '2026-09-06T08:20:00Z', [parking()])
    assert result['status'] == 'covered'
    assert result['matches'][0]['start'].endswith('+02:00')
    assert observed_payment_coverage('bad', LAST, [parking()])['status'] == 'unknown'
    assert observed_payment_coverage(LAST, FIRST, [parking()])['status'] == 'unknown'


def test_month_coverage_never_counts_future_days_or_claims_import_completeness():
    result = month_source_coverage(date(2026, 9, 1), date(2026, 10, 1), date(2026, 9, 6),
                                   {date(2026, 9, 1), date(2026, 9, 6)}, datetime(2026, 9, 6, 12))
    assert result['elapsedDays'] == 6 and result['daysWithRecords'] == 2
    assert len(result['daysWithoutRecords']) == 4 and result['status'] == 'ongoing'
    assert result['lastSuccessfulImport'].endswith('+02:00')


@pytest.mark.parametrize(('today', 'last_success', 'status'), [
    (date(2026, 8, 1), None, 'future'),
    (date(2026, 10, 2), None, 'unknown'),
    (date(2026, 10, 2), datetime(2026, 10, 2), 'review'),
])
def test_month_coverage_status(today, last_success, status):
    result = month_source_coverage(date(2026, 9, 1), date(2026, 10, 1), today, set(), last_success)
    assert result['status'] == status


def schedule(identifier, cron, enabled=True):
    return SimpleNamespace(schedule_id=identifier, cron=cron, enabled=enabled,
                           fan_power=102, water_box_mode=203, mop_mode=300, repeat=1)


def test_next_night_includes_water_pauses_not_manually_disabled_plans():
    robot = {'provider': 'roborock', 'readiness': {'telemetry_at': '2026-09-06T20:00:00+02:00',
              'water_interlock': {'paused_schedules': [{'schedule_id': 'water'}]}}}
    result = night_preparation(robot, [schedule('on', '0 1 * * *'), schedule('water', '0 2 * * *', False),
                                       schedule('manual', '0 3 * * *', False), schedule('day', '0 12 * * *')], datetime(2026, 9, 6, 20))
    assert result['day'] == '2026-09-07'
    assert [row['scheduleId'] for row in result['plans']] == ['on', 'water']
    assert [row['paused'] for row in result['plans']] == [False, True]
    assert result['status'] == 'attention'


def test_next_night_excludes_elapsed_plans_and_missing_data_is_not_ready():
    result = night_preparation({}, [schedule('elapsed', '0 1 * * *'), schedule('next', '0 5 * * *')], datetime(2026, 9, 7, 4))
    assert result['day'] == '2026-09-07'
    assert [row['scheduleId'] for row in result['plans']] == ['next']
    assert result['status'] == 'attention' and result['issues']
