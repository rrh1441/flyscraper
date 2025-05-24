#!/bin/bash
# run_spider.sh — container-compatible version of your legacy trigger

# Navigate to the project root inside the container
cd /app || exit 1

# Run the Scrapy spider with log output
scrapy crawl AncSpider --loglevel=DEBUG >> /app/cron.log 2>&1