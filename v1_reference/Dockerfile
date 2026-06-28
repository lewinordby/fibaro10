FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

COPY v1_reference/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY v1_reference/app ./app
COPY static ./static

EXPOSE 8111

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8111"]
