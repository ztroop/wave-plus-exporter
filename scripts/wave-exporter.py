import asyncio
import logging

import prometheus_client as prom

from wave_plus_exporter import exporter
from wave_plus_exporter.config import load_configuration

logger = logging.getLogger(__name__)

if __name__ == "__main__":
    config = load_configuration()
    listening_port = int(config.get("ListeningPort", 8000))
    logger.info(f"Listening on port {listening_port}.")

    prom.start_http_server(listening_port)
    asyncio.run(exporter(config))
