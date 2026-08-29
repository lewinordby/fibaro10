FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

COPY maintenance_app/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY microapp_backend ./microapp_backend
COPY maintenance_app ./maintenance_app

EXPOSE 8156

CMD ["uvicorn", "maintenance_app.app.main:app", "--host", "0.0.0.0", "--port", "8156"]
