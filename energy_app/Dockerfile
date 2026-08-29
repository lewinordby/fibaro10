FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

COPY energy_app/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY microapp_backend ./microapp_backend
COPY energy_app ./energy_app

EXPOSE 8154

CMD ["uvicorn", "energy_app.app.main:app", "--host", "0.0.0.0", "--port", "8154"]
