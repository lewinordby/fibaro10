FROM python:3.12-slim

WORKDIR /app

COPY sun2_importer/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY sun2_importer/app ./app
COPY sun2_room_mapping.py ./sun2_room_mapping.py

ENV SUN2_IMPORT_DATA_DIR=/data
VOLUME ["/data"]
EXPOSE 8096

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8096"]
