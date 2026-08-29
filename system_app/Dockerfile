FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

COPY system_app/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY microapp_backend ./microapp_backend
COPY system_app ./system_app

EXPOSE 8157

CMD ["uvicorn", "system_app.app.main:app", "--host", "0.0.0.0", "--port", "8157"]
