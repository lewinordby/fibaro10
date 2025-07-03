from fastapi import FastAPI, Request, Depends, Query
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import declarative_base
from sqlalchemy import Column, Integer, Float, String, DateTime, select
import csv
from io import StringIO
from datetime import datetime
import os

DATABASE_URL = os.getenv("DATABASE_URL")

engine = create_async_engine(DATABASE_URL, echo=False)
SessionLocal = async_sessionmaker(bind=engine, expire_on_commit=False)
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


async def get_session() -> AsyncSession:
    async with SessionLocal() as session:
        yield session


@app.on_event("startup")
async def startup():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


@app.post("/log")
async def log_data(
    temperature: float,
    humidity: float = None,
    timestamp: str = None,
    source: str = None,
    session: AsyncSession = Depends(get_session)
):
    timestamp = datetime.fromisoformat(timestamp) if timestamp else datetime.now()
    data = SensorData(
        temperature=temperature,
        humidity=humidity,
        timestamp=timestamp,
        source=source
    )
    session.add(data)
    await session.commit()
    return {"status": "success"}


@app.get("/", response_class=HTMLResponse)
async def index(request: Request, source: str = Query(default=None), session: AsyncSession = Depends(get_session)):
    query = select(SensorData)
    if source:
        query = query.where(SensorData.source == source)
    result = await session.execute(query.order_by(SensorData.timestamp.desc()))
    data = result.scalars().all()
    return templates.TemplateResponse("index.html", {"request": request, "data": data, "source": source or ""})


@app.get("/export")
async def export_csv(session: AsyncSession = Depends(get_session)):
    result = await session.execute(select(SensorData).order_by(SensorData.timestamp.desc()))
    data = result.scalars().all()
    output = StringIO()
    writer = csv.writer(output)
    writer.writerow(["id", "temperature", "humidity", "timestamp", "source"])
    for row in data:
        writer.writerow([row.id, row.temperature, row.humidity, row.timestamp, row.source])
    output.seek(0)
    return StreamingResponse(output, media_type="text/csv", headers={"Content-Disposition": "attachment; filename=data.csv"})
