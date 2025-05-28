#!/bin/bash
# run_spider.sh — container-compatible version of your legacy trigger

# Navigate to the project root inside the container
cd /app || exit 1

# Check for SPIDER_NAME environment variable, default to AncSpider
SPIDER_NAME=${SPIDER_NAME:-AncSpider}

# Run the Scrapy spider with log output
scrapy crawl "$SPIDER_NAME" --loglevel=DEBUG >> /app/cron.log 2>&1