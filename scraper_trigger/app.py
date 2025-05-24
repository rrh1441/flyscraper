#!/usr/bin/env python3
import logging
import subprocess
from flask import Flask, jsonify, request

app = Flask(__name__)

# Set your API key (replace with a strong secret)
EXPECTED_API_KEY = "sImJtxvjQBCYt6OSzvbLWhNlw-7tTIaN1E8yK97nb8k"

@app.route("/trigger_scraper", methods=["POST"])
def trigger_scraper():
    api_key = request.headers.get("x-api-key")
    if api_key != EXPECTED_API_KEY:
        return jsonify({"error": "Unauthorized"}), 401

    try:
        # Command to trigger your scraper; adjust if needed
        command = ["scrapy", "crawl", "AncSpider"]
        result = subprocess.run(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=True
        )
        return jsonify({"status": "success", "output": result.stdout})
    except subprocess.CalledProcessError as e:
        logging.error("Scraper error: %s", e.stderr)
        return jsonify({"status": "error", "message": e.stderr}), 500

if __name__ == "__main__":
    # Listen on all interfaces at port 5000
    app.run(host="0.0.0.0", port=5000)
