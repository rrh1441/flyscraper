# flyscraper/Dockerfile  – one-shot job container

FROM python:3.12-slim

# ---------- system-level build deps ----------
RUN apt-get update && apt-get install -y \
    build-essential \
    libxml2-dev \
    libxslt1-dev \
    libffi-dev \
    libssl-dev \
 && rm -rf /var/lib/apt/lists/*

# ---------- application files ----------
WORKDIR /app

# Scrapy project
COPY CurrentScraper /app

# Spider entry script
COPY run_spider.sh /app/

# ---------- Python dependencies ----------
COPY CurrentScraper/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# ---------- permissions ----------
RUN chmod +x /app/run_spider.sh

# ---------- entrypoint ----------
CMD ["bash", "/app/run_spider.sh"]