
from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy import Column, Integer, Float, String, DateTime
from sqlalchemy.future import select
from datetime import datetime
from typing import Optional
import csv
import io
import os

DATABASE_URL = os.getenv("DATABASE_URL")

engine = create_async_engine(DATABASE_URL, echo=True, future=True)
async_session = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
Base = declarative_base()

app = FastAPI()
templates = Jinja2Templates(directory="templates")

class SensorData(Base):
    __tablename__ = "sensor_data"

    id = Column(Integer, primary_key=True, index=True)
    temperature = Column(Float)
    humidity = Column(Float)
    timestamp = Column(DateTime)
    source = Column(String)

class SensorDataCreate(BaseModel):
    temperature: float
    humidity: Optional[float] = None
    timestamp: datetime
    source: Optional[str] = None

@app.on_event("startup")
async def on_startup():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

@app.post("/log")
async def log_data(data: SensorDataCreate):
    timestamp = data.timestamp.replace(tzinfo=None)
    new_entry = SensorData(
        temperature=data.temperature,
        humidity=data.humidity,
        timestamp=timestamp,
        source=data.source
    )
    async with async_session() as session:
        session.add(new_entry)
        await session.commit()
    return {"status": "success"}

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    async with async_session() as session:
        result = await session.execute(select(SensorData).order_by(SensorData.timestamp.desc()).limit(100))
        entries = result.scalars().all()
    return templates.TemplateResponse("index.html", {"request": request, "entries": entries})

@app.get("/download")
async def download_data():
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["id", "temperature", "humidity", "timestamp", "source"])
    async with async_session() as session:
        result = await session.execute(select(SensorData).order_by(SensorData.timestamp.desc()))
        for entry in result.scalars():
            writer.writerow([
                entry.id,
                entry.temperature,
                entry.humidity,
                entry.timestamp.isoformat(),
                entry.source
            ])
    output.seek(0)
    return StreamingResponse(output, media_type="text/csv", headers={"Content-Disposition": "attachment; filename=data.csv"})
