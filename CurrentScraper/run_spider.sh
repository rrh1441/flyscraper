#!/bin/bash
set -x  # print each command (debug mode)

# 1) Change to the project root (where scrapy.cfg is located)
cd /home/rrh1441/courtscraper_cloud/CurrentScraper || {
  echo "Error: cannot cd to /home/rrh1441/courtscraper_cloud/CurrentScraper"
  exit 1
}

# 2) Activate the known virtual environment
source /home/rrh1441/scraper_trigger/venv/bin/activate

# 3) Make sure logs directory exists
mkdir -p /home/rrh1441/courtscraper_cloud/CurrentScraper/logs

# 4) Run the spider, appending logs to cron.log in your logs directory
/home/rrh1441/scraper_trigger/venv/bin/scrapy crawl AncSpider --loglevel=DEBUG >> /home/rrh1441/courtscraper_cloud/CurrentScraper/logs/cron.log 2>&1
