CREATE TABLE IF NOT EXISTS notification_outbox (
    id BIGSERIAL PRIMARY KEY,
    topic TEXT NOT NULL,
    title TEXT NOT NULL,
    message TEXT NOT NULL,
    tags TEXT,
    priority VARCHAR NOT NULL DEFAULT '3',
    click_url TEXT,
    status VARCHAR NOT NULL DEFAULT 'pending',
    attempts INTEGER NOT NULL DEFAULT 0,
    next_attempt_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
    locked_at TIMESTAMP WITHOUT TIME ZONE,
    sent_at TIMESTAMP WITHOUT TIME ZONE,
    last_error TEXT,
    related_type VARCHAR,
    related_id BIGINT,
    created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_notification_outbox_status_next
    ON notification_outbox (status, next_attempt_at);
CREATE INDEX IF NOT EXISTS ix_notification_outbox_locked_at
    ON notification_outbox (locked_at);
CREATE INDEX IF NOT EXISTS ix_notification_outbox_sent_at
    ON notification_outbox (sent_at);
CREATE INDEX IF NOT EXISTS ix_notification_outbox_related
    ON notification_outbox (related_type, related_id);
