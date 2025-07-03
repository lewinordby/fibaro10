from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy import Column, Integer, Float, String, DateTime
from sqlalchemy.orm import declarative_base
from datetime import datetime
import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

app = FastAPI()

# Statisk og templates
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# Databaseoppsett
Base = declarative_base()
engine = create_async_engine(DATABASE_URL, echo=True)
async_session = async_sessionmaker(engine, expire_on_commit=False)

class SensorData(Base):
    __tablename__ = "sensor_data"

    id = Column(Integer, primary_key=True, index=True)
    temperature = Column(Float, nullable=True)
    humidity = Column(Float, nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
    source = Column(String, default="unknown")

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
async def log_data(data: SensorDataIn):
    async with async_session() as session:
        record = SensorData(
            temperature=data.temperature,
            humidity=data.humidity,
            timestamp=data.timestamp,
            source=data.source,
        )
        session.add(record)
        await session.commit()
    return {"status": "ok"}

@app.get("/", response_class=HTMLResponse)
async def read_data(request: Request, source: str = None):
    async with async_session() as session:
        if source:
            result = await session.execute(
                SensorData.__table__.select().where(SensorData.source == source).order_by(SensorData.timestamp.desc()).limit(100)
            )
        else:
            result = await session.execute(
                SensorData.__table__.select().order_by(SensorData.timestamp.desc()).limit(100)
            )
        rows = result.fetchall()

    return templates.TemplateResponse("table.html", {"request": request, "rows": rows, "source": source or ""})

@app.get("/download")
async def download_csv(source: str = None):
    from fastapi.responses import StreamingResponse
    import csv
    from io import StringIO

    async with async_session() as session:
        if source:
            result = await session.execute(
                SensorData.__table__.select().where(SensorData.source == source).order_by(SensorData.timestamp.desc())
            )
        else:
            result = await session.execute(
                SensorData.__table__.select().order_by(SensorData.timestamp.desc())
            )
        rows = result.fetchall()

    output = StringIO()
    writer = csv.writer(output)
    writer.writerow(["id", "temperature", "humidity", "timestamp", "source"])
    for row in rows:
        writer.writerow([row.id, row.temperature, row.humidity, row.timestamp, row.source])

    output.seek(0)
    return StreamingResponse(output, media_type="text/csv", headers={"Content-Disposition": "attachment; filename=export.csv"})
