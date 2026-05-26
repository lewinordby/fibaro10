FROM mcr.microsoft.com/playwright/python:v1.49.1-jammy

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app

EXPOSE 8109

CMD ["sh", "-c", "Xvfb :99 -screen 0 1365x900x24 -nolisten tcp >/tmp/xvfb.log 2>&1 & export DISPLAY=:99; exec uvicorn app.main:app --host 0.0.0.0 --port 8109"]
