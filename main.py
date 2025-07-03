from fastapi import FastAPI, Request
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
import os
import sqlalchemy
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy import Column, Integer, Float, String, DateTime

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise ValueError("DATABASE_URL must be set as an environment variable.")

# Ensure URL starts with correct async prefix
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql+asyncpg://", 1)

engine = create_async_engine(DATABASE_URL, echo=False)
async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
Base = declarative_base()

class SensorData(Base):
    __tablename__ = "sensor_data"
    id = Column(Integer, primary_key=True, index=True)
    temperature = Column(Float)
    humidity = Column(Float)
    timestamp = Column(DateTime)
    source = Column(String)

class SensorInput(BaseModel):
    temperature: float
    humidity: Optional[float] = None
    timestamp: Optional[str] = None
    source: Optional[str] = "unknown"

app = FastAPI()

@app.on_event("startup")
async def startup():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

@app.post("/log")
async def log_data(data: List[SensorInput], request: Request):
    async with async_session() as session:
        for entry in data:
            try:
                ts = (
                    datetime.fromisoformat(entry.timestamp.replace("Z", "+00:00")).replace(tzinfo=None)
                    if entry.timestamp else datetime.utcnow()
                )
            except Exception as e:
                return {"error": f"Invalid timestamp: {entry.timestamp}", "detail": str(e)}

            record = SensorData(
                temperature=entry.temperature,
                humidity=entry.humidity,
                timestamp=ts,
                source=entry.source or "unknown"
            )
            session.add(record)
        await session.commit()
    return {"message": f"Stored {len(data)} entries."}
