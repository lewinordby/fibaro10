from fastapi import FastAPI, Request, Form, Query
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, DeclarativeBase, Mapped, mapped_column
from sqlalchemy import select
from pydantic import BaseModel
from typing import Optional, List
import csv
import io
import os
from datetime import datetime

DATABASE_URL = os.getenv("DATABASE_URL")

engine = create_async_engine(DATABASE_URL, echo=False)
async_session = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

class Base(DeclarativeBase):
    pass

class SensorData(Base):
    __tablename__ = "sensor_data"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    temperature: Mapped[Optional[float]]
    humidity: Mapped[Optional[float]]
    timestamp: Mapped[datetime]
    source: Mapped[Optional[str]]

class SensorDataInput(BaseModel):
    temperature: Optional[float] = None
    humidity: Optional[float] = None
    timestamp: datetime
    source: Optional[str] = None

app = FastAPI()
templates = Jinja2Templates(directory="templates")

@app.post("/log")
async def log_data(data: List[SensorDataInput]):
    async with async_session() as session:
        session.add_all([SensorData(**item.dict()) for item in data])
        await session.commit()
    return {"message": f"Stored {len(data)} entries."}

@app.get("/", response_class=HTMLResponse)
async def read_data(request: Request, source: Optional[str] = None, limit: int = 100):
    async with async_session() as session:
        stmt = select(SensorData)
        if source:
            stmt = stmt.where(SensorData.source == source)
        stmt = stmt.order_by(SensorData.timestamp.desc()).limit(limit)
        result = await session.execute(stmt)
        data = result.scalars().all()
    return templates.TemplateResponse("data.html", {"request": request, "data": data, "source": source})

@app.get("/export")
async def export_data(source: Optional[str] = None):
    async with async_session() as session:
        stmt = select(SensorData)
        if source:
            stmt = stmt.where(SensorData.source == source)
        stmt = stmt.order_by(SensorData.timestamp.desc())
        result = await session.execute(stmt)
        data = result.scalars().all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["id", "temperature", "humidity", "timestamp", "source"])
    for row in data:
        writer.writerow([row.id, row.temperature, row.humidity, row.timestamp, row.source])
    output.seek(0)

    return StreamingResponse(output, media_type="text/csv", headers={"Content-Disposition": "attachment; filename=data.csv"})