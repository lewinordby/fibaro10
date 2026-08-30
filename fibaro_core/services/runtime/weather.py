"""Weather services with explicit process dependencies."""

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from fibaro_core.models import YrForecastSample
from fibaro_core.schemas import EventDataIn
from sqlalchemy import select
from time import perf_counter
from time_formatting import local_now_naive, sample_bucket
from typing import Any, Callable, Dict, Optional
from zoneinfo import ZoneInfo
import asyncio
import json
import urllib.request


@dataclass
class Dependencies:
    MET_LAT: Any
    MET_LON: Any
    MET_USER_AGENT: Any
    MET_WEATHER_CACHE: Any
    WEATHER_LABELS: Any
    YR_FORECAST_ASSIGNMENTS: Any
    async_session: Callable[..., Any]
    dedupe_samples_by_bucket: Callable[..., Any]
    json_value: Callable[..., Any]
    logger: Any
    nested_extra_value: Callable[..., Any]
    process_locks: Any
    record_import_job: Callable[..., Any]


def create_service(dependencies: Dependencies):

    def weather_label(value) -> Optional[str]:
        WEATHER_LABELS = dependencies.WEATHER_LABELS
        if value in (None, ""):
            return None
        raw = str(value).strip()
        key = raw.lower().replace("-", "_")
        if key in WEATHER_LABELS:
            return WEATHER_LABELS[key]
        for suffix in ("_day", "_night", "_polartwilight"):
            if key.endswith(suffix) and key[: -len(suffix)] in WEATHER_LABELS:
                return WEATHER_LABELS[key[: -len(suffix)]]
        cleaned = raw.replace("_", " ").replace("-", " ")
        return cleaned[:1].upper() + cleaned[1:] if cleaned else None

    def weather_from_rows(*rows) -> Optional[str]:
        nested_extra_value = dependencies.nested_extra_value
        keys = [
            "weather_text",
            "weather_type",
            "yr_weather",
            "weather",
            "condition_text",
            "condition",
            "summary",
            "symbol_code",
            "weather_symbol",
            "yr_symbol",
            "next_1_hours_symbol_code",
        ]
        for row in rows:
            if row is None:
                continue
            for attr in ("weather_text", "weather_type", "yr_weather", "weather_symbol", "yr_symbol"):
                label = weather_label(getattr(row, attr, None))
                if label:
                    return label
            extra = getattr(row, "extra", None)
            found = nested_extra_value(extra, keys)
            label = weather_label(found)
            if label:
                return label
        return None

    def met_time(value: Optional[str]) -> Optional[datetime]:
        if not value:
            return None
        try:
            stamp = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return None
        if stamp.tzinfo:
            stamp = stamp.astimezone(ZoneInfo("UTC")).replace(tzinfo=None)
        return stamp

    def http_header_time(value: Optional[str]) -> Optional[datetime]:
        if not value:
            return None
        try:
            stamp = parsedate_to_datetime(value)
        except (TypeError, ValueError):
            return None
        if stamp.tzinfo:
            stamp = stamp.astimezone(ZoneInfo("UTC")).replace(tzinfo=None)
        return stamp

    def met_age_seconds(value: Optional[str]) -> Optional[int]:
        try:
            return int(value) if value is not None else None
        except (TypeError, ValueError):
            return None

    def met_next_fetch_after(forecast: Optional[Dict[str, Any]], now_value: Optional[datetime] = None) -> datetime:
        now_value = now_value or datetime.utcnow()
        expires_at = (forecast or {}).get("expires_at")
        if isinstance(expires_at, datetime) and expires_at > now_value:
            return expires_at + timedelta(minutes=1)
        return now_value + timedelta(minutes=1)

    def met_details(entry: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        if not entry:
            return {}
        return entry.get("data", {}).get("instant", {}).get("details", {}) or {}

    def met_period_details(entry: Optional[Dict[str, Any]], period: str) -> Dict[str, Any]:
        if not entry:
            return {}
        return entry.get("data", {}).get(period, {}).get("details", {}) or {}

    def met_period_symbol(entry: Optional[Dict[str, Any]]) -> Optional[str]:
        if not entry:
            return None
        data = entry.get("data", {})
        for period in ("next_1_hours", "next_6_hours", "next_12_hours"):
            symbol = data.get(period, {}).get("summary", {}).get("symbol_code")
            if symbol:
                return symbol
        return None

    def met_value(details: Dict[str, Any], key: str) -> Optional[float]:
        value = details.get(key)
        try:
            return float(value) if value is not None else None
        except (TypeError, ValueError):
            return None

    def met_entry_at(timeseries: list[Dict[str, Any]], base_time: Optional[datetime], hours: int) -> Optional[Dict[str, Any]]:
        if not timeseries or not base_time:
            return None
        target = base_time + timedelta(hours=hours)
        entries = [(met_time(entry.get("time")), entry) for entry in timeseries]
        entries = [(stamp, entry) for stamp, entry in entries if stamp is not None]
        if not entries:
            return None
        future_entries = [(stamp, entry) for stamp, entry in entries if stamp >= target]
        source = future_entries or entries
        return min(source, key=lambda item: abs((item[0] - target).total_seconds()))[1]

    def met_forecast_from_payload(payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        timeseries = payload.get("properties", {}).get("timeseries", [])
        if not timeseries:
            return None
        meta = payload.get("properties", {}).get("meta", {}) or {}
        current = timeseries[0]
        forecast_time = met_time(current.get("time"))
        details = met_details(current)
        symbol = met_period_symbol(current)
        next_1h = met_period_details(current, "next_1_hours")
        next_6h = met_period_details(current, "next_6_hours")
        next_12h = met_period_details(current, "next_12_hours")
        next_12h_summary = current.get("data", {}).get("next_12_hours", {}).get("summary", {}) or {}
        forecast: Dict[str, Any] = {
            "symbol": symbol or "",
            "text": weather_label(symbol),
            "api_updated_at": met_time(meta.get("updated_at")),
            "forecast_time": forecast_time,
            "air_temperature": met_value(details, "air_temperature"),
            "air_temperature_percentile_10": met_value(details, "air_temperature_percentile_10"),
            "air_temperature_percentile_90": met_value(details, "air_temperature_percentile_90"),
            "relative_humidity": met_value(details, "relative_humidity"),
            "wind_speed": met_value(details, "wind_speed"),
            "wind_speed_of_gust": met_value(details, "wind_speed_of_gust"),
            "wind_speed_percentile_10": met_value(details, "wind_speed_percentile_10"),
            "wind_speed_percentile_90": met_value(details, "wind_speed_percentile_90"),
            "wind_from_direction": met_value(details, "wind_from_direction"),
            "cloud_area_fraction": met_value(details, "cloud_area_fraction"),
            "cloud_area_fraction_high": met_value(details, "cloud_area_fraction_high"),
            "cloud_area_fraction_medium": met_value(details, "cloud_area_fraction_medium"),
            "cloud_area_fraction_low": met_value(details, "cloud_area_fraction_low"),
            "fog_area_fraction": met_value(details, "fog_area_fraction"),
            "dew_point_temperature": met_value(details, "dew_point_temperature"),
            "air_pressure_at_sea_level": met_value(details, "air_pressure_at_sea_level"),
            "ultraviolet_index_clear_sky": met_value(details, "ultraviolet_index_clear_sky"),
            "precipitation_next_1h": met_value(next_1h, "precipitation_amount"),
            "precipitation_next_1h_min": met_value(next_1h, "precipitation_amount_min"),
            "precipitation_next_1h_max": met_value(next_1h, "precipitation_amount_max"),
            "precipitation_next_6h": met_value(next_6h, "precipitation_amount"),
            "precipitation_next_6h_min": met_value(next_6h, "precipitation_amount_min"),
            "precipitation_next_6h_max": met_value(next_6h, "precipitation_amount_max"),
            "probability_of_precipitation_next_1h": met_value(next_1h, "probability_of_precipitation"),
            "probability_of_precipitation_next_6h": met_value(next_6h, "probability_of_precipitation"),
            "probability_of_precipitation_next_12h": met_value(next_12h, "probability_of_precipitation"),
            "probability_of_thunder_next_1h": met_value(next_1h, "probability_of_thunder"),
            "air_temperature_min_next_6h": met_value(next_6h, "air_temperature_min"),
            "air_temperature_max_next_6h": met_value(next_6h, "air_temperature_max"),
            "symbol_confidence_next_12h": next_12h_summary.get("symbol_confidence"),
        }
        for hours in (1, 3, 6, 12, 24):
            entry = met_entry_at(timeseries, forecast_time, hours)
            forecast[f"temp_{hours}h"] = met_value(met_details(entry), "air_temperature")
            forecast[f"symbol_{hours}h"] = met_period_symbol(entry)
        next_6h_values = []
        if forecast_time:
            for entry in timeseries:
                stamp = met_time(entry.get("time"))
                temp = met_value(met_details(entry), "air_temperature")
                if stamp and temp is not None and forecast_time <= stamp <= forecast_time + timedelta(hours=6):
                    next_6h_values.append(temp)
        forecast["temp_min_next_6h"] = min(next_6h_values) if next_6h_values else None
        forecast["temp_max_next_6h"] = max(next_6h_values) if next_6h_values else None
        forecast["raw_meta"] = meta
        forecast["timeseries_count"] = len(timeseries)
        return forecast if forecast["text"] or forecast["air_temperature"] is not None else None

    def fetch_met_weather() -> Optional[Dict[str, Any]]:
        MET_LAT = dependencies.MET_LAT
        MET_LON = dependencies.MET_LON
        MET_USER_AGENT = dependencies.MET_USER_AGENT
        url = f"https://api.met.no/weatherapi/locationforecast/2.0/complete?lat={MET_LAT:.4f}&lon={MET_LON:.4f}"
        request = urllib.request.Request(
            url,
            headers={
                "Accept": "application/json",
                "User-Agent": MET_USER_AGENT,
            },
        )
        try:
            with urllib.request.urlopen(request, timeout=4) as response:
                headers = response.headers
                payload = json.loads(response.read().decode("utf-8"))
        except (OSError, urllib.error.URLError, json.JSONDecodeError):
            return None
        forecast = met_forecast_from_payload(payload)
        if forecast:
            forecast["last_modified"] = http_header_time(headers.get("Last-Modified"))
            forecast["expires_at"] = http_header_time(headers.get("Expires"))
            forecast["age_seconds"] = met_age_seconds(headers.get("Age"))
            forecast["next_fetch_after"] = met_next_fetch_after(forecast)
            forecast["raw_payload"] = payload
            forecast["raw_headers"] = dict(headers.items())
            forecast["raw_endpoint"] = url
            forecast["raw_coordinates"] = {"lat": MET_LAT, "lon": MET_LON}
        return forecast

    async def met_weather_cached() -> Optional[Dict[str, Any]]:
        MET_WEATHER_CACHE = dependencies.MET_WEATHER_CACHE
        async_session = dependencies.async_session
        json_value = dependencies.json_value
        logger = dependencies.logger
        process_locks = dependencies.process_locks
        record_import_job = dependencies.record_import_job
        now_value = datetime.now(timezone.utc).replace(tzinfo=None)
        if MET_WEATHER_CACHE["expires"] > now_value:
            return MET_WEATHER_CACHE["value"]
        if process_locks.met_weather_fetch_lock is None:
            process_locks.met_weather_fetch_lock = asyncio.Lock()
        async with process_locks.met_weather_fetch_lock:
            now_value = datetime.now(timezone.utc).replace(tzinfo=None)
            if MET_WEATHER_CACHE["expires"] > now_value:
                return MET_WEATHER_CACHE["value"]
            started_at = local_now_naive()
            started_perf = perf_counter()
            value = await asyncio.to_thread(fetch_met_weather)
            finished_at = local_now_naive()
            MET_WEATHER_CACHE["value"] = value
            MET_WEATHER_CACHE["expires"] = met_next_fetch_after(value, now_value) if value else now_value + timedelta(minutes=5)
            try:
                async with async_session() as session:
                    await record_import_job(
                        session,
                        "yr_weather_refresh",
                        ok=value is not None,
                        started_at=started_at,
                        finished_at=finished_at,
                        records_imported=1 if value is not None else 0,
                        records_total=1,
                        duration_seconds=round(perf_counter() - started_perf, 3),
                        message=(
                            f"Ny prognose hentet fra MET ({value.get('text') or value.get('symbol_code') or 'værdata'})."
                            if value is not None
                            else "MET svarte ikke med en gyldig prognose; prøver igjen om 5 minutter."
                        ),
                        raw={
                            "endpoint": value.get("raw_endpoint") if value else None,
                            "forecastTime": json_value(value.get("forecast_time")) if value else None,
                            "nextFetchAfter": MET_WEATHER_CACHE["expires"].replace(tzinfo=timezone.utc).isoformat(),
                            "cacheRefresh": True,
                        },
                    )
                    await session.commit()
            except Exception:
                logger.warning("Could not persist MET refresh status", exc_info=True)
            return value

    async def fetch_yr_cloud_samples(day_start: datetime, day_end: datetime):
        async_session = dependencies.async_session
        dedupe_samples_by_bucket = dependencies.dedupe_samples_by_bucket
        async with async_session() as session:
            sample_result = await session.execute(
                select(YrForecastSample)
                .where(YrForecastSample.bucket_start >= day_start)
                .where(YrForecastSample.bucket_start < day_end)
                .order_by(YrForecastSample.bucket_start.asc(), YrForecastSample.timestamp.asc())
            )
            sample_rows = dedupe_samples_by_bucket(sample_result.scalars().all())

        samples = []
        for row in sample_rows:
            sample_time = row.bucket_start or row.timestamp
            cloud_value = row.cloud_area_fraction
            if sample_time is None or cloud_value is None:
                continue
            samples.append(
                {
                    "time_dt": sample_time,
                    "time": sample_time.strftime("%H:%M"),
                    "cloud_area_fraction": round(float(cloud_value), 1),
                    "weather_text": row.weather_text or "",
                }
            )
        return samples

    def yr_sample_from_forecast(
        timestamp: datetime,
        bucket_start: datetime,
        source: Optional[str],
        forecast: Dict[str, Any],
    ) -> YrForecastSample:
        return YrForecastSample(
            timestamp=timestamp,
            bucket_start=bucket_start,
            source=source or "MET/Yr Locationforecast",
            api_updated_at=forecast.get("api_updated_at"),
            last_modified=forecast.get("last_modified"),
            expires_at=forecast.get("expires_at"),
            next_fetch_after=forecast.get("next_fetch_after"),
            age_seconds=forecast.get("age_seconds"),
            forecast_time=forecast.get("forecast_time"),
            symbol_code=forecast.get("symbol") or None,
            weather_text=forecast.get("text") or None,
            air_temperature=forecast.get("air_temperature"),
            air_temperature_percentile_10=forecast.get("air_temperature_percentile_10"),
            air_temperature_percentile_90=forecast.get("air_temperature_percentile_90"),
            relative_humidity=forecast.get("relative_humidity"),
            wind_speed=forecast.get("wind_speed"),
            wind_speed_of_gust=forecast.get("wind_speed_of_gust"),
            wind_speed_percentile_10=forecast.get("wind_speed_percentile_10"),
            wind_speed_percentile_90=forecast.get("wind_speed_percentile_90"),
            wind_from_direction=forecast.get("wind_from_direction"),
            cloud_area_fraction=forecast.get("cloud_area_fraction"),
            cloud_area_fraction_high=forecast.get("cloud_area_fraction_high"),
            cloud_area_fraction_medium=forecast.get("cloud_area_fraction_medium"),
            cloud_area_fraction_low=forecast.get("cloud_area_fraction_low"),
            fog_area_fraction=forecast.get("fog_area_fraction"),
            dew_point_temperature=forecast.get("dew_point_temperature"),
            air_pressure_at_sea_level=forecast.get("air_pressure_at_sea_level"),
            ultraviolet_index_clear_sky=forecast.get("ultraviolet_index_clear_sky"),
            precipitation_next_1h=forecast.get("precipitation_next_1h"),
            precipitation_next_1h_min=forecast.get("precipitation_next_1h_min"),
            precipitation_next_1h_max=forecast.get("precipitation_next_1h_max"),
            precipitation_next_6h=forecast.get("precipitation_next_6h"),
            precipitation_next_6h_min=forecast.get("precipitation_next_6h_min"),
            precipitation_next_6h_max=forecast.get("precipitation_next_6h_max"),
            probability_of_precipitation_next_1h=forecast.get("probability_of_precipitation_next_1h"),
            probability_of_precipitation_next_6h=forecast.get("probability_of_precipitation_next_6h"),
            probability_of_precipitation_next_12h=forecast.get("probability_of_precipitation_next_12h"),
            probability_of_thunder_next_1h=forecast.get("probability_of_thunder_next_1h"),
            air_temperature_min_next_6h=forecast.get("air_temperature_min_next_6h"),
            air_temperature_max_next_6h=forecast.get("air_temperature_max_next_6h"),
            symbol_confidence_next_12h=forecast.get("symbol_confidence_next_12h"),
            temp_1h=forecast.get("temp_1h"),
            temp_3h=forecast.get("temp_3h"),
            temp_6h=forecast.get("temp_6h"),
            temp_12h=forecast.get("temp_12h"),
            temp_24h=forecast.get("temp_24h"),
            symbol_1h=forecast.get("symbol_1h"),
            symbol_3h=forecast.get("symbol_3h"),
            symbol_6h=forecast.get("symbol_6h"),
            symbol_12h=forecast.get("symbol_12h"),
            symbol_24h=forecast.get("symbol_24h"),
            temp_min_next_6h=forecast.get("temp_min_next_6h"),
            temp_max_next_6h=forecast.get("temp_max_next_6h"),
            extra=yr_sample_extra(forecast),
            raw=yr_sample_raw(forecast),
        )

    def yr_sample_extra(forecast: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "raw_meta": forecast.get("raw_meta") or {},
            "timeseries_count": forecast.get("timeseries_count"),
        }

    def yr_sample_raw(forecast: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "endpoint": forecast.get("raw_endpoint"),
            "coordinates": forecast.get("raw_coordinates"),
            "headers": forecast.get("raw_headers") or {},
            "payload": forecast.get("raw_payload") or {},
        }

    def update_yr_sample_from_forecast(record: YrForecastSample, forecast: Dict[str, Any]) -> None:
        YR_FORECAST_ASSIGNMENTS = dependencies.YR_FORECAST_ASSIGNMENTS
        for attr, key in YR_FORECAST_ASSIGNMENTS:
            value = forecast.get(key)
            if attr == "symbol_code":
                value = value or None
            elif attr == "weather_text":
                value = value or None
            setattr(record, attr, value)
        record.extra = yr_sample_extra(forecast)
        record.raw = yr_sample_raw(forecast)

    async def save_yr_sample_for_payload(data: EventDataIn, forecast: Optional[Dict[str, Any]] = None) -> Optional[int]:
        async_session = dependencies.async_session
        forecast = forecast or await met_weather_cached()
        if not forecast:
            return None
        timestamp = data.timestamp or datetime.utcnow()
        bucket_start = data.bucket_start or sample_bucket(timestamp)
        expires_at = forecast.get("expires_at")
        api_updated_at = forecast.get("api_updated_at")
        async with async_session() as session:
            stmt = select(YrForecastSample).limit(1)
            if expires_at:
                stmt = stmt.where(YrForecastSample.expires_at == expires_at)
            elif api_updated_at:
                stmt = stmt.where(YrForecastSample.api_updated_at == api_updated_at)
            else:
                stmt = stmt.where(YrForecastSample.bucket_start == bucket_start)
            existing = (await session.execute(stmt)).scalars().first()
            if existing:
                update_yr_sample_from_forecast(existing, forecast)
                await session.commit()
                return existing.id
            record = yr_sample_from_forecast(timestamp, bucket_start, data.source, forecast)
            session.add(record)
            await session.commit()
            await session.refresh(record)
            return record.id

    return {
        "fetch_met_weather": fetch_met_weather,
        "fetch_yr_cloud_samples": fetch_yr_cloud_samples,
        "http_header_time": http_header_time,
        "met_age_seconds": met_age_seconds,
        "met_details": met_details,
        "met_entry_at": met_entry_at,
        "met_forecast_from_payload": met_forecast_from_payload,
        "met_next_fetch_after": met_next_fetch_after,
        "met_period_details": met_period_details,
        "met_period_symbol": met_period_symbol,
        "met_time": met_time,
        "met_value": met_value,
        "met_weather_cached": met_weather_cached,
        "save_yr_sample_for_payload": save_yr_sample_for_payload,
        "update_yr_sample_from_forecast": update_yr_sample_from_forecast,
        "weather_from_rows": weather_from_rows,
        "weather_label": weather_label,
        "yr_sample_extra": yr_sample_extra,
        "yr_sample_from_forecast": yr_sample_from_forecast,
        "yr_sample_raw": yr_sample_raw,
    }
