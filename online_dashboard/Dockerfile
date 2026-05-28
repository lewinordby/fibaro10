FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY online_dashboard ./online_dashboard
COPY static ./static

EXPOSE 8111

CMD ["uvicorn", "online_dashboard.app.main:app", "--host", "0.0.0.0", "--port", "8111"]
