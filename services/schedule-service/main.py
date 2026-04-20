#!/usr/bin/env python
"""
Schedule Service - Stub
Заглушка сервиса управления расписанием
"""

import os
import logging
from http.server import HTTPServer, BaseHTTPRequestHandler
import json

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

SERVICE_NAME = os.getenv("SERVICE_NAME", "schedule-service")
SERVICE_PORT = int(os.getenv("SERVICE_PORT", 8082))


class RequestHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/health":
            self.send_response(200)
            self.send_header("Content-type", "application/json")
            self.end_headers()
            response = {"status": "healthy", "service": SERVICE_NAME}
            self.wfile.write(json.dumps(response).encode())
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, format, *args):
        logger.info(format % args)


if __name__ == "__main__":
    server = HTTPServer(("0.0.0.0", SERVICE_PORT), RequestHandler)
    logger.info(f"✅ {SERVICE_NAME} запущен на порту {SERVICE_PORT}")
    server.serve_forever()
