FROM node:22-alpine AS frontend_builder

WORKDIR /frontend

COPY frontend/package*.json ./
RUN npm ci

COPY frontend/ ./
RUN npm run build


FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

COPY app /app/app
COPY --from=frontend_builder /frontend/dist /app/app/frontend_dist

EXPOSE 8128

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8128", "--no-access-log"]
