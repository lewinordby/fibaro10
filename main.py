
from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, StreamingResponse
from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from sqlalchemy import Column, Integer, Float, DateTime, String
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
import csv
import io
import os

DATABASE_URL = os.getenv("DATABASE_URL")

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

class SensorDataIn(BaseModel):
    temperature: float
    humidity: Optional[float] = None
    timestamp: str
    source: Optional[str] = None

app = FastAPI()
templates = Jinja2Templates(directory="templates")
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.on_event("startup")
async def startup():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

@app.post("/log")
async def log_data(log_entry: SensorDataIn, request: Request):
    timestamp = datetime.fromisoformat(log_entry.timestamp.replace("Z", "+00:00")).replace(tzinfo=None)
    async with async_session() as session:
        entry = SensorData(
            temperature=log_entry.temperature,
            humidity=log_entry.humidity,
            timestamp=timestamp,
            source=log_entry.source or request.client.host,
        )
        session.add(entry)
        await session.commit()
    return {"message": "Logged successfully"}

@app.get("/", response_class=HTMLResponse)
async def read_data(request: Request):
    async with async_session() as session:
        result = await session.execute(
            SensorData.__table__.select().order_by(SensorData.timestamp.desc()).limit(100)
        )
        data = result.fetchall()
    return templates.TemplateResponse("index.html", {"request": request, "data": data})

@app.get("/download")
async def download_data():
    async with async_session() as session:
        result = await session.execute(SensorData.__table__.select().order_by(SensorData.timestamp.desc()))
        rows = result.fetchall()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["id", "temperature", "humidity", "timestamp", "source"])
    for row in rows:
        writer.writerow([row.id, row.temperature, row.humidity, row.timestamp, row.source])

    output.seek(0)
    return StreamingResponse(output, media_type="text/csv", headers={"Content-Disposition": "attachment; filename=data.csv"})
