FROM node:24-alpine AS desktop_v2_builder

WORKDIR /app/desktop_v2

COPY desktop_v2/package*.json ./
RUN npm ci

COPY desktop_v2/ ./
RUN npm run build


FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
COPY --from=desktop_v2_builder /app/desktop_v2/dist ./desktop_v2/dist

EXPOSE 8110

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8110"]
