# syntax=docker/dockerfile:1.7
FROM node:24-alpine AS frontend_builder

WORKDIR /workspace
COPY packages/mosaic-theme/package.json ./packages/mosaic-theme/package.json
COPY packages/microapp-ui/package.json ./packages/microapp-ui/package.json
COPY parking_app/frontend/package*.json ./parking_app/frontend/
WORKDIR /workspace/parking_app/frontend
RUN --mount=type=cache,target=/root/.npm npm config set fetch-retries 5 \
    && npm config set fetch-retry-factor 2 \
    && npm config set fetch-retry-mintimeout 20000 \
    && npm config set fetch-retry-maxtimeout 120000 \
    && npm ci

WORKDIR /workspace
COPY packages/mosaic-theme ./packages/mosaic-theme
COPY packages/microapp-ui ./packages/microapp-ui
COPY parking_app/frontend/ ./parking_app/frontend/
WORKDIR /workspace/parking_app/frontend
RUN npm run build


FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

COPY parking_app/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY microapp_backend ./microapp_backend
COPY parking_app ./parking_app
COPY --from=frontend_builder /workspace/parking_app/frontend/dist ./parking_app/app/static/dist

EXPOSE 8152

CMD ["uvicorn", "parking_app.app.main:app", "--host", "0.0.0.0", "--port", "8152"]
