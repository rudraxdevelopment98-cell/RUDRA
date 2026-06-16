# RUDRA brain — portable image so it runs on a PC, server, or Raspberry Pi.
FROM python:3.11-slim

WORKDIR /app

# Install deps first for better layer caching.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# App code.
COPY core ./core
COPY shared ./shared

# The brain.
CMD ["python", "-m", "core.main"]
