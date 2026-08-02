# syntax=docker/dockerfile:1.7
FROM node:24-alpine AS frontend_builder

WORKDIR /workspace
COPY packages/mosaic-theme/package.json ./packages/mosaic-theme/package.json
COPY shell_app/frontend/package*.json ./shell_app/frontend/
WORKDIR /workspace/shell_app/frontend
RUN --mount=type=cache,target=/root/.npm npm ci
WORKDIR /workspace
COPY packages/mosaic-theme ./packages/mosaic-theme
COPY shell_app/frontend/ ./shell_app/frontend/
WORKDIR /workspace/shell_app/frontend
RUN npm run build

FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
WORKDIR /app

COPY shell_app/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt
COPY shell_app ./shell_app
COPY --from=frontend_builder /workspace/shell_app/frontend/dist ./shell_app/app/static/dist

EXPOSE 8150
CMD ["uvicorn", "shell_app.app.main:app", "--host", "0.0.0.0", "--port", "8150"]
