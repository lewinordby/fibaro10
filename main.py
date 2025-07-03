import os
import logging
from datetime import datetime, timezone
from typing import List, Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy import Float, String, Column, Integer, DateTime
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.exc import SQLAlchemyError

# --- Logging ---
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- Environment ---
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    logger.error("Environment variable DATABASE_URL is missing.")
    raise RuntimeError("DATABASE_URL is not set in environment variables.")

# --- Database setup ---
engine = create_async_engine(DATABASE_URL, echo=False)
async_session = async_sessionmaker(engine, expire_on_commit=False)

class Base(DeclarativeBase):
    pass

class SensorData(Base):
    __tablename__ = "sensor_data"

    id = Column(Integer, primary_key=True, index=True)
    temperature = Column(Float)
    humidity = Column(Float)
    timestamp = Column(DateTime(timezone=False))  # naive datetime
    source = Column(String)

# --- Pydantic model ---
class SensorReading(BaseModel):
    temperature: float
    humidity: Optional[float] = Field(None)
    timestamp: datetime
    source: str

    def to_naive_utc(self) -> "SensorReading":
        ts = self.timestamp
        if
