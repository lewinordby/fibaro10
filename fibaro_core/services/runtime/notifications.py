"""Notifications services with explicit process dependencies."""

from dataclasses import dataclass
from datetime import datetime, timedelta
from fibaro_core.models import AlarmEvent, NotificationOutbox
from sqlalchemy import and_, func, or_, select
from time_formatting import api_local_iso, local_now_naive
from typing import Any, Callable, Optional
from urllib.parse import quote, quote_plus, urlparse
import asyncio
import urllib.request


@dataclass
class Dependencies:
    NTFY_ACCESS_COOLDOWN_MINUTES: Any
    NTFY_ACCESS_TOPIC: Any
    NTFY_BASE_URL: Any
    NTFY_BOLLARDS_TOPIC: Any
    NTFY_DOORS_TOPIC: Any
    NTFY_LIGHTS_TOPIC: Any
    NTFY_OUTBOX_POLL_SECONDS: Any
    NTFY_OUTBOX_RETRY_BASE_SECONDS: Any
    NTFY_OUTBOX_RETRY_MAX_SECONDS: Any
    NTFY_OUTBOX_STALE_LOCK_SECONDS: Any
    NTFY_TIMEOUT_SECONDS: Any
    NTFY_VENTILATION_TOPIC: Any
    async_session: Callable[..., Any]
    logger: Any


def create_service(dependencies: Dependencies):

    def ntfy_host() -> str:
        NTFY_BASE_URL = dependencies.NTFY_BASE_URL
        parsed = urlparse(NTFY_BASE_URL)
        return parsed.netloc or parsed.path.strip("/")

    def ntfy_topic_url(topic: str) -> str:
        NTFY_BASE_URL = dependencies.NTFY_BASE_URL
        return f"{NTFY_BASE_URL}/{quote(topic, safe='')}"

    def ntfy_subscribe_url(topic: str, display_name: str) -> str:
        return f"ntfy://{ntfy_host()}/{quote(topic, safe='')}?display={quote_plus(display_name)}"

    def ntfy_subscription_rows(bollard_status: Optional[dict[str, Any]] = None) -> list[dict[str, Any]]:
        NTFY_ACCESS_COOLDOWN_MINUTES = dependencies.NTFY_ACCESS_COOLDOWN_MINUTES
        NTFY_ACCESS_TOPIC = dependencies.NTFY_ACCESS_TOPIC
        NTFY_BOLLARDS_TOPIC = dependencies.NTFY_BOLLARDS_TOPIC
        NTFY_DOORS_TOPIC = dependencies.NTFY_DOORS_TOPIC
        NTFY_LIGHTS_TOPIC = dependencies.NTFY_LIGHTS_TOPIC
        NTFY_VENTILATION_TOPIC = dependencies.NTFY_VENTILATION_TOPIC
        bollard_settings = bollard_status.get("settings") if isinstance(bollard_status, dict) else {}
        if not isinstance(bollard_settings, dict):
            bollard_settings = {}
        definitions = [
            {
                "key": "doors",
                "title": "Døralarmer",
                "area": "Dører og solrom",
                "topic": NTFY_DOORS_TOPIC,
                "display_name": "SUN2 dørvarsler",
                "description": "Varsler når et solrom er lukket uten tilhørende soltime, eller når kunden blir vesentlig lenger enn forventet.",
                "triggers": ["Lukket uten soltime", "For lang tid etter soltime", "Prioriterte døravvik"],
                "priority": "Høy",
                "publishing_enabled": True,
            },
            {
                "key": "bollards",
                "title": "Pullerter og trapp",
                "area": "Kamera og bygg",
                "topic": NTFY_BOLLARDS_TOPIC,
                "display_name": "Pullert- og trappevarsler",
                "description": "Varsler om bekreftede visuelle endringer på pullerter og trappa ved Solstudio. Bilder og analysedata sendes ikke til ntfy.",
                "triggers": ["Bekreftet endring på pullert", "Bekreftet endring på trapp"],
                "priority": "Høy",
                "publishing_enabled": bool(bollard_settings.get("notification_enabled")),
            },
            {
                "key": "lights",
                "title": "Lysstyring",
                "area": "Lys",
                "topic": NTFY_LIGHTS_TOPIC,
                "display_name": "SUN2 lys",
                "description": "Varsler ved PÅ- og AV-hendelser fra HC3, med lux og årsak når dette finnes i hendelsen.",
                "triggers": ["Lys slås på", "Lys slås av"],
                "priority": "Normal",
                "publishing_enabled": True,
            },
            {
                "key": "ventilation",
                "title": "Ventilasjon",
                "area": "Ventilasjon",
                "topic": NTFY_VENTILATION_TOPIC,
                "display_name": "SUN2 ventilasjon",
                "description": "Varsler ved PÅ- og AV-hendelser for vifter og avfukter, med modus, temperaturer og fuktighet når tilgjengelig.",
                "triggers": ["Vifte eller avfukter slås på", "Vifte eller avfukter slås av"],
                "priority": "Normal",
                "publishing_enabled": True,
            },
            {
                "key": "access",
                "title": "Brukeraktivitet",
                "area": "Tilgang",
                "topic": NTFY_ACCESS_TOPIC,
                "display_name": "SUN2 tilgang",
                "description": "Varsler når en ordinær bruker logger inn, og deretter høyst periodisk mens brukeren benytter løsningen. Master varsles ikke om egen bruk.",
                "triggers": ["Innlogging", f"Videre bruk etter minst {int(NTFY_ACCESS_COOLDOWN_MINUTES)} minutter"],
                "priority": "Normal",
                "publishing_enabled": True,
            },
        ]
        rows = []
        for definition in definitions:
            topic = str(definition.get("topic") or "")
            display_name = str(definition.get("display_name") or "")
            configured = bool(topic)
            public_definition = {
                key: value
                for key, value in definition.items()
                if key not in {"topic", "display_name", "publishing_enabled"}
            }
            rows.append(
                {
                    **public_definition,
                    "configured": configured,
                    "publishingEnabled": configured and bool(definition.get("publishing_enabled")),
                    "subscribeUrl": ntfy_subscribe_url(topic, display_name) if configured else "",
                    "webUrl": ntfy_topic_url(topic) if configured else "",
                }
            )
        return rows

    def publish_ntfy_message(
        topic: str,
        title: str,
        message: str,
        tags: str = "",
        priority: str = "3",
        click_url: str = "",
    ) -> None:
        NTFY_TIMEOUT_SECONDS = dependencies.NTFY_TIMEOUT_SECONDS
        headers = {"Title": title, "Priority": priority}
        if tags:
            headers["Tags"] = tags
        if click_url:
            headers["Click"] = click_url
        request = urllib.request.Request(
            ntfy_topic_url(topic),
            data=message.encode("utf-8"),
            headers=headers,
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=NTFY_TIMEOUT_SECONDS):
            pass

    def notification_retry_delay_seconds(attempts: int) -> int:
        NTFY_OUTBOX_RETRY_BASE_SECONDS = dependencies.NTFY_OUTBOX_RETRY_BASE_SECONDS
        NTFY_OUTBOX_RETRY_MAX_SECONDS = dependencies.NTFY_OUTBOX_RETRY_MAX_SECONDS
        exponent = max(0, min(16, int(attempts or 0) - 1))
        return min(NTFY_OUTBOX_RETRY_MAX_SECONDS, NTFY_OUTBOX_RETRY_BASE_SECONDS * (2**exponent))

    def notification_outbox_row(
        topic: str,
        title: str,
        message: str,
        tags: str = "",
        priority: str = "3",
        click_url: str = "",
        related_type: str = "",
        related_id: Optional[int] = None,
    ) -> NotificationOutbox:
        now = datetime.utcnow()
        return NotificationOutbox(
            topic=topic.strip(),
            title=title.strip(),
            message=message.strip(),
            tags=tags.strip() or None,
            priority=str(priority or "3"),
            click_url=click_url.strip() or None,
            status="pending",
            attempts=0,
            next_attempt_at=now,
            related_type=related_type.strip() or None,
            related_id=related_id,
            created_at=now,
            updated_at=now,
        )

    async def enqueue_ntfy_message(
        topic: str,
        title: str,
        message: str,
        tags: str = "",
        priority: str = "3",
        click_url: str = "",
        related_type: str = "",
        related_id: Optional[int] = None,
        session=None,
    ) -> bool:
        async_session = dependencies.async_session
        if not topic.strip() or not message.strip():
            return False
        row = notification_outbox_row(
            topic,
            title,
            message,
            tags,
            priority,
            click_url,
            related_type,
            related_id,
        )
        if session is not None:
            session.add(row)
            await session.flush()
            return True
        async with async_session() as own_session:
            own_session.add(row)
            await own_session.commit()
        return True

    async def claim_notification_outbox_row() -> Optional[dict[str, Any]]:
        NTFY_OUTBOX_STALE_LOCK_SECONDS = dependencies.NTFY_OUTBOX_STALE_LOCK_SECONDS
        async_session = dependencies.async_session
        now = datetime.utcnow()
        stale_before = now - timedelta(seconds=NTFY_OUTBOX_STALE_LOCK_SECONDS)
        eligible = or_(
            NotificationOutbox.status.in_(("pending", "retry")),
            and_(
                NotificationOutbox.status == "sending",
                or_(NotificationOutbox.locked_at.is_(None), NotificationOutbox.locked_at < stale_before),
            ),
        )
        async with async_session() as session:
            row = (
                await session.execute(
                    select(NotificationOutbox)
                    .where(eligible)
                    .where(NotificationOutbox.next_attempt_at <= now)
                    .order_by(NotificationOutbox.next_attempt_at.asc(), NotificationOutbox.id.asc())
                    .with_for_update(skip_locked=True)
                    .limit(1)
                )
            ).scalars().first()
            if row is None:
                return None
            row.status = "sending"
            row.attempts = int(row.attempts or 0) + 1
            row.locked_at = now
            row.updated_at = now
            await session.commit()
            return {
                "id": row.id,
                "topic": row.topic,
                "title": row.title,
                "message": row.message,
                "tags": row.tags or "",
                "priority": row.priority or "3",
                "click_url": row.click_url or "",
                "attempts": row.attempts,
                "related_type": row.related_type,
                "related_id": row.related_id,
            }

    async def finish_notification_outbox_row(item: dict[str, Any], error: Optional[Exception] = None) -> None:
        async_session = dependencies.async_session
        now = datetime.utcnow()
        alarm_now = local_now_naive()
        async with async_session() as session:
            row = await session.get(NotificationOutbox, item["id"])
            if row is None:
                return
            row.locked_at = None
            row.updated_at = now
            if error is None:
                row.status = "sent"
                row.sent_at = now
                row.last_error = None
                if row.related_type == "alarm_event" and row.related_id:
                    alarm = await session.get(AlarmEvent, row.related_id)
                    if alarm is not None:
                        alarm.notification_status = "sent"
                        alarm.notification_count = int(alarm.notification_count or 0) + 1
                        alarm.first_notification_at = alarm.first_notification_at or alarm_now
                        alarm.last_notification_at = alarm_now
                        alarm.updated_at = alarm_now
            else:
                row.status = "retry"
                row.last_error = str(error)[:2000]
                row.next_attempt_at = now + timedelta(seconds=notification_retry_delay_seconds(row.attempts))
            await session.commit()

    async def notification_outbox_worker() -> None:
        NTFY_OUTBOX_POLL_SECONDS = dependencies.NTFY_OUTBOX_POLL_SECONDS
        logger = dependencies.logger
        while True:
            try:
                item = await claim_notification_outbox_row()
                if item is None:
                    await asyncio.sleep(NTFY_OUTBOX_POLL_SECONDS)
                    continue
                try:
                    await asyncio.to_thread(
                        publish_ntfy_message,
                        item["topic"],
                        item["title"],
                        item["message"],
                        item["tags"],
                        item["priority"],
                        item["click_url"],
                    )
                except Exception as exc:
                    logger.warning(
                        "NTFY-varsel %s feilet (forsok %s), prover igjen: %s",
                        item["id"],
                        item["attempts"],
                        exc,
                    )
                    await finish_notification_outbox_row(item, exc)
                else:
                    await finish_notification_outbox_row(item)
            except asyncio.CancelledError:
                raise
            except Exception:
                logger.exception("Uventet feil i NTFY-utkoarbeider")
                await asyncio.sleep(max(1.0, NTFY_OUTBOX_POLL_SECONDS))

    async def notification_outbox_status(session) -> dict[str, Any]:
        rows = (
            await session.execute(
                select(NotificationOutbox.status, func.count(NotificationOutbox.id)).group_by(NotificationOutbox.status)
            )
        ).all()
        counts = {str(status): int(count or 0) for status, count in rows}
        oldest = (
            await session.execute(
                select(func.min(NotificationOutbox.created_at)).where(
                    NotificationOutbox.status.in_(("pending", "retry", "sending"))
                )
            )
        ).scalar_one_or_none()
        return {
            "status": "warning" if counts.get("retry", 0) else "ok",
            "pending": counts.get("pending", 0),
            "sending": counts.get("sending", 0),
            "retrying": counts.get("retry", 0),
            "sent": counts.get("sent", 0),
            "oldestPendingAt": api_local_iso(oldest),
        }

    def bollard_mobile_notification_payload(status: dict[str, Any]) -> dict[str, Any]:
        NTFY_BOLLARDS_TOPIC = dependencies.NTFY_BOLLARDS_TOPIC
        settings = status.get("settings") if isinstance(status.get("settings"), dict) else {}
        summary = status.get("summary") if isinstance(status.get("summary"), dict) else {}
        runtime = status.get("runtime") if isinstance(status.get("runtime"), dict) else {}
        topic_configured = bool(NTFY_BOLLARDS_TOPIC) and bool(runtime.get("notification_configured"))
        return {
            "channelName": "Pullerter og trapp ved Solstudio",
            "configured": topic_configured,
            "enabled": bool(settings.get("notification_enabled")),
            "monitoringReady": bool(summary.get("monitoring_ready")),
            "activeIncidents": int(summary.get("active_incidents") or 0),
            "lastCheckAt": runtime.get("last_success_at"),
            "subscribeUrl": ntfy_subscribe_url(NTFY_BOLLARDS_TOPIC, "Pullert- og trappevarsler") if NTFY_BOLLARDS_TOPIC else "",
            "webUrl": ntfy_topic_url(NTFY_BOLLARDS_TOPIC) if NTFY_BOLLARDS_TOPIC else "",
            "provider": ntfy_host(),
            "privacy": "Kun alarmtekst sendes. Bilder, registreringsnummer og analysedata forblir lokale.",
        }

    async def save_record(record, notification: Optional[dict[str, Any]] = None) -> int:
        async_session = dependencies.async_session
        async with async_session() as session:
            session.add(record)
            await session.flush()
            if notification:
                await enqueue_ntfy_message(
                    **notification,
                    related_type=getattr(record, "__tablename__", record.__class__.__name__),
                    related_id=getattr(record, "id", None),
                    session=session,
                )
            await session.commit()
            await session.refresh(record)
            return record.id

    return {
        "bollard_mobile_notification_payload": bollard_mobile_notification_payload,
        "claim_notification_outbox_row": claim_notification_outbox_row,
        "enqueue_ntfy_message": enqueue_ntfy_message,
        "finish_notification_outbox_row": finish_notification_outbox_row,
        "notification_outbox_row": notification_outbox_row,
        "notification_outbox_status": notification_outbox_status,
        "notification_outbox_worker": notification_outbox_worker,
        "notification_retry_delay_seconds": notification_retry_delay_seconds,
        "ntfy_host": ntfy_host,
        "ntfy_subscribe_url": ntfy_subscribe_url,
        "ntfy_subscription_rows": ntfy_subscription_rows,
        "ntfy_topic_url": ntfy_topic_url,
        "publish_ntfy_message": publish_ntfy_message,
        "save_record": save_record,
    }
