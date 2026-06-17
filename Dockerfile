# RUDRA — portable image so it runs on a PC, server, Raspberry Pi, or a host
# like Railway/Render/Fly. Serves the web dashboard + API by default; run
# `python -m core.main` instead for the headless CLI/voice loop.
FROM python:3.11-slim

WORKDIR /app

# Install deps first for better layer caching.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# App code.
COPY core ./core
COPY shared ./shared
COPY server ./server
COPY dashboard ./dashboard

# Most hosts (Railway, Render, Fly) inject $PORT; default to 8080 locally.
ENV PORT=8080
# Unbuffered stdout so crash tracebacks actually reach the host's log stream
# instead of sitting in a buffer that's never flushed.
ENV PYTHONUNBUFFERED=1
EXPOSE 8080

CMD ["sh", "-c", "uvicorn server.app:app --host 0.0.0.0 --port ${PORT}"]
