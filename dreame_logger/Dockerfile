FROM python:3.12-slim AS upstream

ARG DREAME_UPSTREAM_COMMIT=3720223e11353aba622f8da34c9041586865aa48
RUN apt-get update \
    && apt-get install -y --no-install-recommends git ca-certificates \
    && git clone --filter=blob:none https://github.com/Tasshack/dreame-vacuum.git /vendor \
    && git -C /vendor checkout --detach "$DREAME_UPSTREAM_COMMIT" \
    && rm -rf /vendor/.git /var/lib/apt/lists/*
COPY sanitize_upstream.py /tmp/sanitize_upstream.py
RUN python /tmp/sanitize_upstream.py

FROM python:3.12-slim

WORKDIR /app
COPY requirements.txt .
RUN apt-get update \
    && apt-get install -y --no-install-recommends gcc libc6-dev \
    && pip install --no-cache-dir -r requirements.txt \
    && apt-get purge -y --auto-remove gcc libc6-dev \
    && rm -rf /var/lib/apt/lists/*

COPY --from=upstream /vendor/custom_components/dreame_vacuum/dreame /opt/dreame-vacuum/dreame
COPY --from=upstream /vendor/LICENSE /opt/dreame-vacuum/LICENSE
COPY app ./app
COPY BUILD ./BUILD

ENV PYTHONPATH=/opt/dreame-vacuum
ENV DREAME_DATA_DIR=/data
VOLUME ["/data"]
EXPOSE 8094

HEALTHCHECK --interval=30s --timeout=10s --retries=3 --start-period=45s \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8094/health', timeout=5).read()"

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8094"]
