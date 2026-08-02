# syntax=docker/dockerfile:1.7
FROM node:24-alpine AS frontend_builder
WORKDIR /workspace
COPY packages/mosaic-theme/package.json ./packages/mosaic-theme/package.json
COPY packages/microapp-ui/package.json ./packages/microapp-ui/package.json
COPY operations_app/frontend/package*.json ./operations_app/frontend/
WORKDIR /workspace/operations_app/frontend
RUN --mount=type=cache,target=/root/.npm npm ci
WORKDIR /workspace
COPY packages/mosaic-theme ./packages/mosaic-theme
COPY packages/microapp-ui ./packages/microapp-ui
COPY operations_app/frontend/ ./operations_app/frontend/
WORKDIR /workspace/operations_app/frontend
RUN npm run build

FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
COPY operations_app/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt
COPY microapp_backend ./microapp_backend
COPY operations_app ./operations_app
COPY --from=frontend_builder /workspace/operations_app/frontend/dist ./operations_app/app/static/dist
EXPOSE 8155
CMD ["uvicorn", "operations_app.app.main:app", "--host", "0.0.0.0", "--port", "8155"]
