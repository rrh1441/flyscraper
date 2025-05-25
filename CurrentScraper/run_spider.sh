#!/usr/bin/env bash
set -euo pipefail          # fail on first error
set -x                     # echo commands (debug)

ROOT=/home/rrh1441/courtscraper_cloud/CurrentScraper
VENV=/home/rrh1441/scraper_trigger/venv
LOG_DIR="$ROOT/logs"
LOG_FILE="$LOG_DIR/cron.log"

mkdir -p "$LOG_DIR"
cd "$ROOT"

source "$VENV/bin/activate"

iso_now() { date -Is; }

echo "[$(iso_now)] 🚀  Spider starting…" | tee -a "$LOG_FILE"

# Scrapy → stdout **and** log file
scrapy crawl AncSpider --loglevel=INFO 2>&1 | tee -a "$LOG_FILE"

echo "[$(iso_now)] ✅  Finished (exit $?)" | tee -a "$LOG_FILE"