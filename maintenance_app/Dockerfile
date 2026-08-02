# syntax=docker/dockerfile:1.7
FROM node:24-alpine AS frontend_builder
WORKDIR /workspace
COPY packages/mosaic-theme/package.json ./packages/mosaic-theme/package.json
COPY packages/microapp-ui/package.json ./packages/microapp-ui/package.json
COPY maintenance_app/frontend/package*.json ./maintenance_app/frontend/
WORKDIR /workspace/maintenance_app/frontend
RUN --mount=type=cache,target=/root/.npm npm ci
WORKDIR /workspace
COPY packages/mosaic-theme ./packages/mosaic-theme
COPY packages/microapp-ui ./packages/microapp-ui
COPY maintenance_app/frontend/ ./maintenance_app/frontend/
WORKDIR /workspace/maintenance_app/frontend
RUN npm run build

FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
COPY maintenance_app/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt
COPY microapp_backend ./microapp_backend
COPY maintenance_app ./maintenance_app
COPY --from=frontend_builder /workspace/maintenance_app/frontend/dist ./maintenance_app/app/static/dist
EXPOSE 8156
CMD ["uvicorn", "maintenance_app.app.main:app", "--host", "0.0.0.0", "--port", "8156"]
