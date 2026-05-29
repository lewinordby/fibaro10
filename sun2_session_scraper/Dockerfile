FROM mcr.microsoft.com/playwright/python:v1.49.0-jammy

WORKDIR /app

RUN apt-get update \
    && DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends tzdata \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app

VOLUME ["/data"]
EXPOSE 8098

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8098"]
