from fastapi import FastAPI, Request, Depends, Form
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import declarative_base, mapped_column
from sqlalchemy import Float, String, DateTime, select
from datetime import datetime
from typing import Optional, List
import csv
import io
import os

DATABASE_URL = os.getenv("DATABASE_URL")

engine = create_async_engine(DATABASE_URL, echo=False)
async_session = async_sessionmaker(engine, expire_on_commit=False)
Base = declarative_base()

app = FastAPI()
templates = Jinja2Templates(directory="templates")

class SensorData(Base):
    __tablename__ = "sensor_data"

    id = mapped_column(primary_key=True)
    temperature = mapped_column(Float)
    humidity = mapped_column(Float)
    timestamp = mapped_column(DateTime)
    source = mapped_column(String)

class SensorDataIn(BaseModel):
    temperature: float
    humidity: float
    timestamp: datetime
    source: str

@app.on_event("startup")
async def startup():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

@app.post("/log")
async def log_data(data: List[SensorDataIn], session: AsyncSession = Depends(async_session)):
    for entry in data:
        db_entry = SensorData(**entry.model_dump())
        session.add(db_entry)
    await session.commit()
    return {"message": f"Stored {len(data)} entries."}

@app.get("/", response_class=HTMLResponse)
async def read_data(request: Request,
                    source: Optional[str] = None,
                    from_date: Optional[str] = None,
                    to_date: Optional[str] = None,
                    session: AsyncSession = Depends(async_session)):
    stmt = select(SensorData)
    if source:
        stmt = stmt.where(SensorData.source == source)
    if from_date:
        stmt = stmt.where(SensorData.timestamp >= datetime.fromisoformat(from_date))
    if to_date:
        stmt = stmt.where(SensorData.timestamp <= datetime.fromisoformat(to_date))
    result = await session.execute(stmt)
    data = result.scalars().all()
    return templates.TemplateResponse("index.html", {
        "request": request,
        "data": data,
        "source": source or "",
        "from_date": from_date or "",
        "to_date": to_date or ""
    })

@app.get("/export")
async def export_data(source: Optional[str] = None,
                      from_date: Optional[str] = None,
                      to_date: Optional[str] = None,
                      session: AsyncSession = Depends(async_session)):
    stmt = select(SensorData)
    if source:
        stmt = stmt.where(SensorData.source == source)
    if from_date:
        stmt = stmt.where(SensorData.timestamp >= datetime.fromisoformat(from_date))
    if to_date:
        stmt = stmt.where(SensorData.timestamp <= datetime.fromisoformat(to_date))
    result = await session.execute(stmt)
    data = result.scalars().all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["id", "temperature", "humidity", "timestamp", "source"])
    for row in data:
        writer.writerow([row.id, row.temperature, row.humidity, row.timestamp.isoformat(), row.source])

    output.seek(0)
    return StreamingResponse(output, media_type="text/csv", headers={"Content-Disposition": "attachment; filename=data.csv"})