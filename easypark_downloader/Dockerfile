FROM mcr.microsoft.com/playwright/python:v1.49.1-jammy

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV NODE_OPTIONS=--unhandled-rejections=none

RUN apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates curl gnupg \
    && curl -fsSL https://packages.microsoft.com/keys/microsoft.asc | gpg --dearmor -o /usr/share/keyrings/microsoft-edge.gpg \
    && echo "deb [arch=amd64 signed-by=/usr/share/keyrings/microsoft-edge.gpg] https://packages.microsoft.com/repos/edge stable main" > /etc/apt/sources.list.d/microsoft-edge.list \
    && apt-get update \
    && apt-get install -y --no-install-recommends microsoft-edge-stable novnc websockify x11vnc \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app

EXPOSE 8109 6080

CMD ["sh", "-c", "rm -f /tmp/.X99-lock /tmp/.X11-unix/X99; Xvfb :99 -screen 0 1365x900x24 -nolisten tcp >/tmp/xvfb.log 2>&1 & export DISPLAY=:99; VNC_PASSWORD=\"${EASYPARK_VNC_PASSWORD:-$FIBARO10_PASSWORD}\"; if [ -n \"$VNC_PASSWORD\" ]; then x11vnc -display :99 -forever -shared -rfbport 5900 -passwd \"$VNC_PASSWORD\" -quiet -bg >/tmp/x11vnc.log 2>&1; else x11vnc -display :99 -forever -shared -rfbport 5900 -nopw -quiet -bg >/tmp/x11vnc.log 2>&1; fi; websockify --web=/usr/share/novnc/ 6080 localhost:5900 >/tmp/novnc.log 2>&1 & exec uvicorn app.main:app --host 0.0.0.0 --port 8109"]
