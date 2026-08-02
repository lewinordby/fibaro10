FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /srv

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . ./unifi_protect_events

EXPOSE 8130

CMD ["uvicorn", "unifi_protect_events.app.main:app", "--host", "0.0.0.0", "--port", "8130"]
