# syntax=docker/dockerfile:1.7
FROM node:24-alpine AS frontend_builder
WORKDIR /workspace
COPY packages/mosaic-theme/package.json ./packages/mosaic-theme/package.json
COPY packages/microapp-ui/package.json ./packages/microapp-ui/package.json
COPY link_app/frontend/package*.json ./link_app/frontend/
WORKDIR /workspace/link_app/frontend
RUN --mount=type=cache,target=/root/.npm npm ci
WORKDIR /workspace
COPY packages/mosaic-theme ./packages/mosaic-theme
COPY packages/microapp-ui ./packages/microapp-ui
COPY link_app/frontend/ ./link_app/frontend/
WORKDIR /workspace/link_app/frontend
RUN npm run build

FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
COPY link_app/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt
COPY microapp_backend ./microapp_backend
COPY link_app ./link_app
COPY --from=frontend_builder /workspace/link_app/frontend/dist ./link_app/app/static/dist
EXPOSE 8158
CMD ["uvicorn", "link_app.app.main:app", "--host", "0.0.0.0", "--port", "8158"]
