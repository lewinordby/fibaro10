"""Shared configuration needed by both models and domain logic.

The composition root loads dotenv before importing domain modules.
"""

import os

SUN2_AXIS_SNAPSHOT_OFFSET_SECONDS = max(0, int(os.getenv("SUN2_AXIS_SNAPSHOT_OFFSET_SECONDS", "15")))
