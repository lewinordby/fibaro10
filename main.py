from fastapi import FastAPI, Request, HTTPException, Query
from fastapi.responses import HTMLResponse, StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from db import async_session, engine
from models import Base, SensorData
import datetime
import io
import csv

app = FastAPI()

@app.on_event("startup")
async def startup():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

@app.post("/log")
async def log_data(request: Request):
    try:
        data = await request.json()
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid JSON: {e}")

    source = data.get("source")
    timestamp = data.get("timestamp")
    temperatures = data.get("temperatures", [])
    humidities = data.get("humidities", [])

    if not source:
        raise HTTPException(status_code=400, detail="Missing 'source'")
    if not timestamp:
        raise HTTPException(status_code=400, detail="Missing 'timestamp'")
    if not isinstance(temperatures, list) or len(temperatures) != 5:
        raise HTTPException(status_code=400, detail="Expected 5 temperature values")
    if not isinstance(humidities, list) or len(humidities) != 5:
        raise HTTPException(status_code=400, detail="Expected 5 humidity values")

    try:
        parsed_timestamp = datetime.datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid timestamp format: {e}")

    async with async_session() as session:
        for i in range(5):
            entry = SensorData(
                temperature=float(temperatures[i]),
                humidity=float(humidities[i]),
                timestamp=parsed_timestamp,
                source=source
            )
            session.add(entry)
        await session.commit()

    return {"message": "All sensor values logged"}

@app.get("/", response_class=HTMLResponse)
async def read_data(source: str = Query(None)):
    async with async_session() as session:
        stmt = select(SensorData).order_by(SensorData.timestamp.desc()).limit(100)
        if source:
            stmt = stmt.where(SensorData.source == source)
        result = await session.execute(stmt)
        data = result.scalars().all()

    html = "<html><head><title>Sensor Data</title></head><body><h1>Sensor Data</h1>"
    html += "<form method='get'><label for='source'>Filter by source:</label>"
    html += "<input type='text' name='source' value='{0}'><input type='submit' value='Filter'></form>".format(source or "")
    html += "<a href='/export?source={0}'>Download CSV</a><br><br>".format(source or "")
    html += "<table border='1'><tr><th>Source</th><th>Temperature</th><th>Humidity</th><th>Timestamp</th></tr>"
    for entry in data:
        html += f"<tr><td>{entry.source}</td><td>{entry.temperature}</td><td>{entry.humidity}</td><td>{entry.timestamp}</td></tr>"
    html += "</table></body></html>"

    return HTMLResponse(content=html)

@app.get("/export")
async def export_csv(source: str = Query(None)):
    async with async_session() as session:
        stmt = select(SensorData).order_by(SensorData.timestamp.desc())
        if source:
            stmt = stmt.where(SensorData.source == source)
        result = await session.execute(stmt)
        data = result.scalars().all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Source", "Temperature", "Humidity", "Timestamp"])
    for entry in data:
        writer.writerow([entry.source, entry.temperature, entry.humidity, entry.timestamp])

    output.seek(0)
    return StreamingResponse(output, media_type="text/csv", headers={"Content-Disposition": "attachment; filename=sensor_data.csv"})