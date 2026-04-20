#!/usr/bin/env python
"""
Parser Service - Stub
Parses schedule data from external internet sources.
"""

import json
import logging
import os
from http.server import BaseHTTPRequestHandler, HTTPServer

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

SERVICE_NAME = os.getenv("SERVICE_NAME", "parser-service")
SERVICE_PORT = int(os.getenv("SERVICE_PORT", 8082))


class RequestHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/health":
            self.send_response(200)
            self.send_header("Content-type", "application/json")
            self.end_headers()
            response = {"status": "healthy", "service": SERVICE_NAME}
            self.wfile.write(json.dumps(response).encode())
            return

        self.send_response(404)
        self.end_headers()

    def log_message(self, fmt, *args):
        logger.info(fmt % args)


if __name__ == "__main__":
    server = HTTPServer(("0.0.0.0", SERVICE_PORT), RequestHandler)
    logger.info("%s started on port %s", SERVICE_NAME, SERVICE_PORT)
    server.serve_forever()
