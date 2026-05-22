FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app

ENV SUN2_IMPORT_DATA_DIR=/data
VOLUME ["/data"]
EXPOSE 8096

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8096"]
