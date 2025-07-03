from fastapi import FastAPI, Request, HTTPException
from pydantic import BaseModel
from typing import List
from datetime import datetime
import os
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy import Column, Integer, Float, String, DateTime

DATABASE_URL = (
    f"postgresql+asyncpg://{os.getenv('DB_USER')}:{os.getenv('DB_PASS')}@"
    f"{os.getenv('DB_HOST')}:{os.getenv('DB_PORT')}/{os.getenv('DB_NAME')}"
)

# DB setup
engine = create_async_engine(DATABASE_URL, echo=False)
async_session = sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
Base = declarative_base()

# DB model
class SensorData(Base):
    __tablename__ = "sensor_data"
    id = Column(Integer, primary_key=True, index=True)
    temperature = Column(Float)
    humidity = Column(Float)
    timestamp = Column(DateTime)  # naive datetime
    source = Column(String)

# Request schema
class SensorDataIn(BaseModel):
    temperature: float
    humidity: float
    timestamp: str
    source: str

app = FastAPI()

@app.post("/log")
async def log_data(payload: List[SensorDataIn]):
    try:
        records = []
        for entry in payload:
            try:
                # Fjern 'Z' og gjør timestamp offset-naiv
                ts = datetime.fromisoformat(entry.timestamp.replace("Z", "")).replace(tzinfo=None)
            except Exception:
                raise HTTPException(status_code=400, detail=f"Ugyldig timestamp: {entry.timestamp}")

            record = SensorData(
                temperature=entry.temperature,
                humidity=entry.humidity,
                timestamp=ts,
                source=entry.source
            )
            records.append(record)

        async with async_session() as session:
            session.add_all(records)
            await session.commit()

        return {"status": "ok", "saved": len(records)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
