ALTER TABLE roborock_door_automations
ADD COLUMN IF NOT EXISTS minimum_interval_minutes INTEGER NOT NULL DEFAULT 60;
