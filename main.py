from fastapi import FastAPI, Request, Query
from fastapi.responses import HTMLResponse, StreamingResponse
from pydantic import BaseModel, Field
from typing import List, Optional
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy import Column, Integer, Float, String, DateTime, select
from starlette.templating import Jinja2Templates
from starlette.responses import RedirectResponse
import csv
import io
from datetime import datetime
import os

DATABASE_URL = os.environ.get("DATABASE_URL")
engine = create_async_engine(DATABASE_URL, echo=False)
SessionLocal = sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
Base = declarative_base()
templates = Jinja2Templates(directory="templates")

app = FastAPI()

class SensorData(Base):
    __tablename__ = "sensor_data"

    id = Column(Integer, primary_key=True, index=True)
    temperature = Column(Float)
    humidity = Column(Float)
    timestamp = Column(DateTime)
    source = Column(String)

class SensorDataIn(BaseModel):
    temperature: float
    humidity: float
    timestamp: datetime
    source: str

@app.on_event("startup")
async def on_startup():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

@app.get("/", include_in_schema=False)
def root():
    return RedirectResponse(url="/view")

@app.post("/log")
async def log_data(data: List[SensorDataIn]):
    async with SessionLocal() as session:
        entries = [SensorData(**entry.dict()) for entry in data]
        session.add_all(entries)
        await session.commit()
    return {"message": f"Stored {len(data)} entries."}

@app.get("/view", response_class=HTMLResponse)
async def view_data(request: Request, source: Optional[str] = None, date: Optional[str] = None):
    async with SessionLocal() as session:
        stmt = select(SensorData)
        if source:
            stmt = stmt.where(SensorData.source == source)
        if date:
            try:
                dt = datetime.strptime(date, "%Y-%m-%d")
                stmt = stmt.where(SensorData.timestamp.between(dt, dt.replace(hour=23, minute=59, second=59)))
            except:
                pass
        result = await session.execute(stmt)
        data = result.scalars().all()
    return templates.TemplateResponse("view.html", {"request": request, "data": data})

@app.get("/export")
async def export_data(source: Optional[str] = None, date: Optional[str] = None):
    async with SessionLocal() as session:
        stmt = select(SensorData)
        if source:
            stmt = stmt.where(SensorData.source == source)
        if date:
            try:
                dt = datetime.strptime(date, "%Y-%m-%d")
                stmt = stmt.where(SensorData.timestamp.between(dt, dt.replace(hour=23, minute=59, second=59)))
            except:
                pass
        result = await session.execute(stmt)
        data = result.scalars().all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["id", "temperature", "humidity", "timestamp", "source"])
    for d in data:
        writer.writerow([d.id, d.temperature, d.humidity, d.timestamp.isoformat(), d.source])

    output.seek(0)
    return StreamingResponse(output, media_type="text/csv", headers={"Content-Disposition": "attachment; filename=export.csv"})