#!/usr/bin/env python3
"""
Keep-alive script to ping your Render service every 10 minutes
to prevent it from spinning down.

Run this on any always-on machine (your computer, VPS, etc.)
"""

import requests
import time
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

RENDER_URL = "https://ai-agent-ydbu.onrender.com/"
PING_INTERVAL = 600  # 10 minutes

def ping_service():
    try:
        response = requests.get(RENDER_URL, timeout=10)
        if response.status_code == 200:
            logger.info(f"✅ Service is alive: {RENDER_URL}")
        else:
            logger.warning(f"⚠️  Service responded with status {response.status_code}")
    except Exception as e:
        logger.error(f"❌ Failed to ping service: {e}")

if __name__ == "__main__":
    logger.info(f"Starting keep-alive for {RENDER_URL}")
    logger.info(f"Pinging every {PING_INTERVAL} seconds")

    while True:
        ping_service()
        time.sleep(PING_INTERVAL)